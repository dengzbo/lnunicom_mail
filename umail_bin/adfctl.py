# CENO-ADF control script
#
#  Author: Hover
# Version: 1.3
#

import copy, getopt, re, os, sys, string, signal, stat, types, platform
from os import system, popen, path, makedirs, listdir
from os.path import basename, dirname, isdir, isfile
from time import sleep, localtime, strftime
from xml.dom import minidom, Node
from zipfile import ZipFile
from subprocess import Popen

def get_userhome():
    return path.expanduser('~')

def has_method(obj, method_name):
    n = method_name
    return hasattr(obj, n) and type(getattr(obj, n)) == types.MethodType

def has_merge_operation(obj):
    return has_method(obj, 'merge_to')

def merge_attrs(object_from, object_to, names):
    assert object_from is not None, 'object_from is required'
    assert object_to is not None, 'object_to is required'
    for name in names:
        if not hasattr(object_from, name):
            continue
        attr_from = getattr(object_from, name)
        if not hasattr(object_to, name):
            setattr(object_to, name, copy.deepcopy(attr_from))
            continue
        attr_to = getattr(object_to, name)
        if has_merge_operation(attr_from) and has_merge_operation(attr_to):
            attr_from.merge_to(attr_to)
            continue
        if type(attr_from) in (types.ListType, types.TupleType) and type(attr_to) == types.ListType:
            for item in reversed(attr_from):
                attr_to.insert(0, item)
            continue

class Singleton(object):
    def __new__(type):
        if not hasattr(type, '_the_instance'):
            type._the_instance = object.__new__(type)
        return type._the_instance
    def _is_initted(self):
        if not hasattr(self, '_initted'):
            self._initted = True
            return False
        return True

class GlobalSetting(Singleton):
    def __init__(self):
        if self._is_initted():
            return
        self.verbose_mode = False
        self.java_debug_mode = False
        
        # Script Name, this name would be use in show_usage() functiion: umail etc.
        self.script_name = None
        
        self.hostname = ''

class SystemEnv(Singleton):
    def __init__(self):
        if self._is_initted():
            return

        self.__re_key = re.compile('\$([a-zA-Z][a-zA-Z0-9_]*)')
        self.__env = os.environ

    def setEnv(self, key, value):
        setting = GlobalSetting()
        debug('set env %s=%s' % (key, value))
        self.__env[key] = value

    def getEnv(self, key, defaultValue = None):
        env = self.__env
        if env.has_key(key):
            return env[key]
        else:
            return defaultValue

    def resolve(self, expr):
        count = 1
        while count < 100:
            result = self.__re_key.search(expr)
            if result is not None:
                key = result.group(1)
                value = self.getEnv(key, '')
                expr = expr.replace('$' + key, value, 1)
            else:
                break
            count = count + 1
        return expr

class ConfigProperty(Singleton):
    def __init__(self):
        if self._is_initted():
            return

        self.__props = {}
        self.__re_key = re.compile('\$\{([a-zA-Z0-9_\-\.]+)}')

    def setProperty(self, name, value):
        self.__props[name] = value

    def getProperty(self, name, defaultValue = None):
        props = self.__props
        if props.has_key(name):
            return props[name]
        else:
            return defaultValue

    def resolve(self, expr):
        count = 1
        while count < 100:
            result = self.__re_key.search(expr)
            if result is not None:
                key = result.group(1)
                value = self.getProperty(key, '')
                expr = expr.replace('${' + key + '}', value, 1)
            else:
                break
            count = count + 1
        return expr

def debug(msg):
    setting = GlobalSetting()
    if setting.verbose_mode:
        print msg

def resolve_str(source):
    envs = SystemEnv()
    configs = ConfigProperty()

    result = envs.resolve(source)
    result = configs.resolve(result)

    return result

def resolve_attrs(obj, *attr_names):
    for name in attr_names:
        if hasattr(obj, name):
            attrvalue = getattr(obj, name)
            if has_method(attrvalue, 'resolve'):
                attrvalue.resolve()
                continue
            if type(attrvalue) in (types.StringType, types.UnicodeType):
                setattr(obj, name, resolve_str(attrvalue))

def list_child_elements(node, name):
    result = []
    for child in node.childNodes:
        if (child.nodeType == Node.ELEMENT_NODE) and (child.localName == name):
            result.append(child)
    return result

def get_first_child_element(node, name):
    children = list_child_elements(node, name)
    if children:
        return children[0]
    else:
        return None

def has_child_element(node, name):
    for child in node.childNodes:
        if child.nodeType == Node.ELEMENT_NODE and child.localName == name:
            return True
    return False

def check_attribute(element, attributeName):
    assert element.hasAttribute(attributeName),\
            'in <%s>, attr \'%s\' is required' % (element.nodeName, attributeName)

def check_attributes(element, attributeNames):
    for name in attributeNames:
        check_attribute(element, name)

def get_attribute(element, attributeName, check = False):
    if check:
        check_attribute(element, attributeName)
    return element.getAttribute(attributeName)

def fetch_attrs(instance, element, names, check = False):
    if check:
        check_attributes(element, names)
    for name in names:
        if element.hasAttribute(name):
            instance.__dict__[name] = element.getAttribute(name)

def str_value(value):
    if type(value) in (types.StringType, types.UnicodeType):
        return '\'%s\'' % value
    if type(value) == types.ListType:
        return '[%s]' % (', '.join([str_value(i) for i in value]))
    if type(value) == types.TupleType:
        return '(%s)' % (', '.join([str_value(i) for i in value]))
    if type(value) == types.DictType:
        return '{%s}' % (', '.join(['%s=%s' % (k, str_value(v)) for k, v in value.iteritems()]))
    return str(value)

def str_object(obj, attr_names):
    attrs_desc = []
    for name in attr_names:
        if hasattr(obj, name):
            attr = getattr(obj, name)
            attrs_desc.append('%s=%s' % (name, str_value(attr)))
    return '%s{%s}' % (obj.__class__.__name__, ', '.join(attrs_desc))

class SimpleObject:
    def __init__(self):
        self.attrs = []
        self.required_attrs = []
        
    def add_required_attr(self, *attrs):
        self.required_attrs.extend(attrs)

    def add_attr(self, *attrs):
        self.attrs.extend(attrs)

    def parse(self, e):
        fetch_attrs(self, e, self.required_attrs, True)
        fetch_attrs(self, e, self.attrs)

    def resolve(self):
        for name in self.all_attrs():
            if hasattr(self, name):
                resolve_attrs(self, name)

    def all_attrs(self):
        all = []
        all.extend(self.required_attrs)
        all.extend(self.attrs)
        return all

    def merge_to(self, target):
        merge_attrs(self, target, self.all_attrs())

    def __str__(self):
        return str_object(self, self.all_attrs())

class Property(SimpleObject):
    def __init__(self):
        SimpleObject.__init__(self)
        self.add_required_attr('name', 'value')

class EnvSetting(Property):
    def __init__(self):
        Property.__init__(self)

class JavaOptionSupervisor(SimpleObject):
    def __init__(self):
        SimpleObject.__init__(self)
        self.add_required_attr('base')
        self.add_attr('name')

        self.name = 'jnohup'

    def build_option(self):
        return '%s/%s' % (self.base, self.name)

class JavaOptionUser(SimpleObject):
    def __init__(self):
        SimpleObject.__init__(self)
        self.add_attr('name', 'group', 'uid', 'gid')
    def build_option(self):
        # TODO: handle group, uid and gid
        return self.name

class JavaOptionLauncher(SimpleObject):
    def __init__(self):
        SimpleObject.__init__(self)
        self.add_required_attr('class')

class JavaOptionMemory(SimpleObject):
    def __init__(self):
        SimpleObject.__init__(self)
        self.add_attr('min', 'max', 'stack_size', 'incgc', 'noclassgc')
    def build_option(self):
        opts = []
        if hasattr(self, 'min'):
            opts.append('-Xms%s' % self.min)
        if hasattr(self, 'max'):
            opts.append('-Xmx%s' % self.max)
        if hasattr(self, 'stack_size'):
            opts.append('-Xss%s' % self.stack_size)
        if hasattr(self, 'incgc'):
            opts.append('-Xincgc')
        if hasattr(self, 'noclassgc'):
            opts.append('-Xnoclassgc')
        return ' '.join(opts)

class JavaOptionLogger(SimpleObject):
    def __init__(self):
        SimpleObject.__init__(self)
        self.add_required_attr('priority')
        self.add_attr('pattern')
    def build_option(self):
        if hasattr(self, 'pattern'):
            return '-Dnaisa.log.%s.priority=%s -Dcom.ceno.log.%s.priority=%s' % \
                                            (self.pattern, self.priority, self.pattern, self.priority)
        else:
            return '-Dnaisa.log.priority=%s -Dcom.ceno.log.priority=%s' % ((self.priority,) * 2)

class JavaOptionDebug(SimpleObject):
    def __init__(self):
        SimpleObject.__init__(self)
        self.add_required_attr('port')
    def build_option(self):
        setting = GlobalSetting()
        if setting.java_debug_mode:
            print '[launcher  ] INFO : Java debug port is %s' % self.port
            return '-Xdebug -Xnoagent -Djava.compiler=NONE -Xrunjdwp:transport=dt_socket,server=y,suspend=n,address=%s' % self.port
        return ''

class JavaOptionClasspath(SimpleObject):
    def __init__(self):
        SimpleObject.__init__(self)
        self.add_attr('run', 'mode', 'file', 'dir')
        
        self.mode = 'append'

    def build_path(self):
        return path.os.pathsep.join(self.get_files())

    def get_files(self):
        files = []
        if hasattr(self, 'file'):
            files.append(self.file)
        else:
            if isdir(self.dir):
                for filename in listdir(self.dir):
                    if filename.endswith('.jar') or filename.endswith('.zip'):
                        files.append(path.join(self.dir, filename))
        return files

class JavaOptionBootClasspath(SimpleObject):
    def __init__(self):
        SimpleObject.__init__(self)
        self.add_required_attr('file')
        self.add_attr('mode')

        self.mode = 'default'
    def get_files(self):
        return [self.file]

class JavaOptionVerbose(SimpleObject):
    def __init__(self):
        SimpleObject.__init__(self)
        self.add_attr('class', 'gc', 'jni')

class JavaOptionExtend(SimpleObject):
    def __init__(self):
        SimpleObject.__init__(self)
        self.add_required_attr('option')

class JavaOptionProperty(Property):
    def __init__(self):
        Property.__init__(self)

class JavaOptionRotatelogs(SimpleObject):
    def __init__(self):
        SimpleObject.__init__(self)
        self.add_required_attr('pattern')

class JavaOptionJdk(SimpleObject):
    def __init__(self):
        SimpleObject.__init__(self)
        self.add_required_attr('home')
        self.add_attr('exe')

    def get_java_exe(self):
        if not hasattr(self, 'exe') or (self.exe is None):
            return path.join(self.home, 'bin', 'java')
        else:
            return path.join(self.home, 'bin', self.exe)

class JavaOption:
    def __init__(self):
        self.vm_mode = 'server'
        self.props = []
        self.boot_classpaths = []
        self.classpaths = []
        self.extends = []
        self.launcher = JavaOptionLauncher()
        setattr(self.launcher, 'class', 'com.ceno.launcher.Launcher')

        self.attrs = ['vm_mode', 'supervisor', 'user', 'launcher', 'memory',\
                      'logger', 'debug', 'boot_classpaths', 'classpaths', 'extends',\
                      'verbose', 'props', 'rotatelogs', 'jdk']

    def get_launcher_class(self):
        return getattr(self.launcher, 'class')

    def get_java_exe(self):
        if not hasattr(self, 'jdk') or (self.jdk is None):
            home = check_env('JAVA_HOME')
            return path.join(home, 'bin', 'java')
        else:
            return self.jdk.get_java_exe()
            
    def get_cp(self):
        cps = []
        for cp in self.classpaths:
            if cp.mode == 'prepend':
                cps.insert(0, cp.build_path())
            else:
                cps.append(cp.build_path())
        return path.os.pathsep.join(cps)

    def get_opts(self):
        opts = []

        if self.vm_mode:
            opts.append('-' + self.vm_mode)

        for bcp in self.boot_classpaths:
            pattern = '-Xbootclasspath:%s'
            if bcp.mode == 'default':
                pattern = '-Xbootclasspath:%s'
            elif bcp.mode == 'append':
                pattern = '-Xbootclasspath/a:%s'
            elif bcp.mode == 'prepend':
                pattern = '-Xbootclasspath/p:%s'
            else:
                print 'WARN: invalid boot classpath mode %s' % bcp.mode
            opts.append(pattern % bcp.file)

        for attr_name in ('memory', 'logger', 'debug'):
            if hasattr(self, attr_name):
                attr_value = getattr(self, attr_name)
                if has_method(attr_value, 'build_option'):
                    opt = attr_value.build_option()
                    if opt:
                        opts.append(opt)

        if hasattr(self, 'verbose'):
            verbose = self.verbose
            default_mode = True
            for attr_name in ('class', 'gc', 'jni'):
                if hasattr(verbose, attr_name):
                    opts.append('-verbose:%s' % attr_name)
                    default_mode = False
            if default_mode:
                opts.append('-verbose')

        for p in self.props:
            opts.append('-D%s=%s' % (p.name, p.value))

        for ex in self.extends:
            opts.append('-X%s' % ex.option)

        return ' '.join(opts)

    def merge_to(self, target):
        merge_attrs(self, target, self.attrs)

    def __str__(self):
        return str_object(self, self.attrs)

    def resolve(self):
        configs = ConfigProperty()
        for p in self.props:
            k, v = resolve_str(p.name), resolve_str(p.value)
            configs.setProperty(k, v)

        for name in self.attrs:
            resolve_attrs(self, name)

        for bcp in self.boot_classpaths:
            bcp.resolve()

        for cp in self.classpaths:
            cp.resolve()

        for p in self.props:
            p.resolve()

        for ex in self.extends:
            ex.resolve()

        if hasattr(self, 'jdk'):
            self.jdk.resolve()
        
    def parse(self, element):
        vm_mode_element = get_first_child_element(element, 'vm-mode')
        if vm_mode_element is not None:
            self.vm_mode = get_attribute(vm_mode_element, 'mode', True)

        for name, cls in {'supervisor' : JavaOptionSupervisor,\
                     'user' : JavaOptionUser,\
                     'launcher' : JavaOptionLauncher,\
                     'memory' : JavaOptionMemory,\
                     'logger' : JavaOptionLogger,\
                     'debug' : JavaOptionDebug,\
                     'verbose' : JavaOptionVerbose,\
                     'rotatelogs' : JavaOptionRotatelogs,\
                     'jdk' : JavaOptionJdk}.iteritems():

            child_element = get_first_child_element(element, name)
            if child_element is not None:
                obj = cls()
                obj.parse(child_element)
                setattr(self, name, obj)

        for bootcp_element in list_child_elements(element, 'boot-classpath'):
            bootcp = JavaOptionBootClasspath()
            bootcp.parse(bootcp_element)
            self.boot_classpaths.append(bootcp)

        for cp_element in list_child_elements(element, 'classpath'):
            cp = JavaOptionClasspath()
            cp.parse(cp_element)
            self.classpaths.append(cp)

        for prop_element in list_child_elements(element, 'property'):
            prop = JavaOptionProperty()
            prop.parse(prop_element)
            self.props.append(prop)

        for ex_element in list_child_elements(element, 'extend'):
            extend = JavaOptionExtend()
            extend.parse(ex_element)
            self.extends.append(extend)

class ShellOption(SimpleObject):
    def __init__(self):
        SimpleObject.__init__(self)
        self.add_required_attr('command')
    def resolve(self):
        resolve_attrs(self, 'command')

class BootOption:
    BOOT_TYPE_JAVA = 1
    BOOT_TYPE_SHELL = 2

    def __init__(self):
        self.bootable = True
        self.boot_type = self.BOOT_TYPE_JAVA
        self.envs = []
        self.java_option = JavaOption()
        self.shell_option = ShellOption()

    def merge_to(self, target):
        # bootable
        target.bootable = self.bootable and target.bootable

        # boot_type
        if (self.boot_type == self.BOOT_TYPE_SHELL) or (target.boot_type == self.BOOT_TYPE_SHELL):
            target.boot_type = self.BOOT_TYPE_SHELL

        merge_attrs(self, target, ['envs', 'java_option', 'shell_option'])

    def resolve(self):
        envs = SystemEnv()
        for env in self.envs:
            k, v = resolve_str(env.name), resolve_str(env.value)
            envs.setEnv(k, v)
            env.resolve()

        resolve_attrs(self, 'java_option', 'shell_option')

    def parse(self, element):
        if element.hasAttribute('bootable'):
            bootable = element.getAttribute('bootable')
            if bootable is not None and 'false' == bootable.lower():
                self.bootable = False

        if not self.bootable:
            return

        for env_element in list_child_elements(element, 'env'):
            env_setting = EnvSetting()
            env_setting.parse(env_element)
            self.envs.append(env_setting)

        java_element = get_first_child_element(element, 'java')
        if java_element is not None:
            self.java_option.parse(java_element)

        shell_element = get_first_child_element(element, 'shell')
        if shell_element is not None:
            self.boot_type = self.BOOT_TYPE_SHELL
            self.shell_option.parse(shell_element)

    def __str__(self):
        return str_object(self, ('bootable', 'boot_type', 'envs', 'java_option', 'shell_option'))

class DefaultOption(Singleton):
    def __init__(self):
        if self._is_initted():
            return
        self.option = BootOption()
    def __str__(self):
        return str_object(self, ('option',))

class ServerDefine:
    def __init__(self):
        self.option = BootOption()
        self.classpaths = []
    def parse(self, e):
        self.server_type = get_attribute(e, 'type', True)
        self.server_port = get_attribute(e, 'port')
        boot_element = get_first_child_element(e, 'boot')
        if boot_element is not None:
            self.option.parse(boot_element)
        for cp_element in list_child_elements(e, 'classpath'):
            cp = JavaOptionClasspath()
            cp.parse(cp_element)
            self.classpaths.append(cp)
    def __str__(self):
        return str_object(self, ('server_type', 'option', 'classpaths'))
    def resolve(self):
        resolve_attrs(self, 'server_type', 'option')
        for cp in self.classpaths:
            cp.resolve()

class ServerMap(Singleton):
    def __init__(self):
        if self._is_initted():
            return
        self.map = {}
    def __str__(self):
        return str_object(self, ('map',))

class HostDefine:
    def __init__(self, hostname):
        self.hostname = hostname
        self.servers = {}
    def __str__(self):
        return str_object(self, ('hostname', 'servers'))

class HostMap(Singleton):
    def __init__(self):
        if self._is_initted():
            return
        self.map = {}
    def __str__(self):
        return str_object(self, ('map',))

def parse_config_by_doc(doc):
    default_option = DefaultOption()
    server_map = ServerMap()
    host_map = HostMap()

    root = doc.documentElement

    configs = ConfigProperty()
    config_element = get_first_child_element(root, 'config')
    for prop_element in list_child_elements(config_element, 'property'):
        prop = Property()
        prop.parse(prop_element)
        configs.setProperty(configs.resolve(prop.name), configs.resolve(prop.value))

    cube_element = get_first_child_element(root, 'cube')
    if cube_element is None:
        cube_element = get_first_child_element(root, 'main')
    default_element = get_first_child_element(cube_element, 'default')
    servers_element = get_first_child_element(cube_element, 'servers')
    hosts_element = get_first_child_element(cube_element, 'hosts')

    default_boot_element = get_first_child_element(default_element, 'boot')
    default_option.option.parse(default_boot_element)

    for server_element in list_child_elements(servers_element, 'server'):
        server_define = ServerDefine()
        server_define.parse(server_element)
        server_map.map[server_define.server_type] = server_define

    for host_element in list_child_elements(hosts_element, 'host'):
        hostname = get_attribute(host_element, 'name', True)
        host_define = HostDefine(hostname)
        for server_element in list_child_elements(host_element, 'server'):
            host_server_define = ServerDefine()
            host_server_define.parse(server_element)
            host_define.servers[host_server_define.server_type] = host_server_define
        host_map.map[hostname] = host_define

def get_doc_by_string(content):
    pstart = content.find('<?')
    pend = content.find('?>', pstart + 2)

    if pstart >= 0 and pend >= 0:
        head = content[pstart : (pend + 2)]
        pattern1 = re.compile('( *encoding="[a-zA-Z\\-_]+")')
        pattern2 = re.compile('( *encoding=\'[a-zA-Z\\-_]+\')')
        result = pattern1.search(head)
        if not result:
            result = pattern2.search(head)
        if result:
            match = result.group(1)
            head = head.replace(match, '', 1)
            content = head + content[(pend + 2):]

    try:
        return minidom.parseString(content)
    except Exception, e:
        print 'WARN: parse error: %s' % e

def parse_config(filename):
    f = open(filename, 'r')
    content = f.read()
    f.close()

    doc = get_doc_by_string(content)
    if doc is None:
        print 'Check %s! parse error' % filename
        sys.exit(1)
    
    parse_config_by_doc(doc)

def merge_options():
    configs = ConfigProperty()
    default_option = DefaultOption()
    server_map = ServerMap()
    host_map = HostMap()

    default_option.option.resolve()

    for server_define in server_map.map.values():
        default_option.option.merge_to(server_define.option)
        configs.setProperty('server_type', server_define.server_type)
        server_define.resolve()

    for host_define in host_map.map.values():
        for host_server_define in host_define.servers.values():
            server_type = host_server_define.server_type
            if not server_map.map.has_key(server_type):
                print 'WARN: server define "%s" not found' % server_type
                host_server_define.option.bootable = False
                continue
            server_define = server_map.map[server_type]
            if hasattr(server_define, 'server_port'):
                host_server_define.server_port = server_define.server_port
            server_define.option.merge_to(host_server_define.option)
            configs.setProperty('server_type', host_server_define.server_type)
            host_server_define.option.resolve()

def get_local_hostname():
    fh = popen('hostname')
    hostname = fh.read()
    fh.close()
    return hostname.strip()

def get_hostname():
    setting = GlobalSetting()
    hostname = setting.hostname
    if not hostname:
        hostname = get_local_hostname()
    return hostname

def find_pid(target):
    configs = ConfigProperty()
    osid = configs.getProperty('osid')

    pscmd = 'ps -ef'
    if osid == 'win':
        pscmd = 'tasklist'
    fps = popen(pscmd)
    lines = fps.readlines()
    fps.close()
    
    for line in lines:
        if line:
            line = line.strip()
        if not line:
            continue
        fields = re.split(' +', line)
        if fields[1] == target:
            return True
    return False

def kill_proc(pid):
    # SIGKILL -> 9, SIGTERM -> 15
    try:
        if find_pid(pid):
            os.kill(int(pid), signal.SIGTERM)
            sleep(2)
            if find_pid(pid):
                print 'Cannot kill process(%s) by SIGTERM, trying SIGKILL' % pid
                os.kill(int(pid), signal.SIGKILL)
                sleep(1)
                if find_pid(pid):
                    print 'Process(%s) cannot be killed.' % pid
                    return False
    except OSError, e:
        print e
    return True

def get_pid_by_file(pid_file):
    if not isfile(pid_file):
        return None
    f = open(pid_file, 'r')
    pid = f.readline()
    f.close()
    if pid:
        return pid.strip()
    else:
        return None

def run_by_shell(*commands):
    setting = GlobalSetting()
    p = popen('/bin/sh', 'w')
    for cmd in commands:
        debug('shell: %s' % cmd)
        p.write(cmd + os.linesep)
    p.close()

def get_local_servers():
    hosts = HostMap().map
    hostname = get_hostname()
    if not hosts.has_key(hostname):
        print 'ERROR: host %s not found!' % hostname
        return None
    host = hosts[hostname]
    return [s.server_type for s in host.servers.values() if s.option.bootable]

def list_local_servers():
    hostname = get_hostname()
    servers = get_local_servers()
    if servers is None:
        return
    print 'Available servers at [%s]:' % hostname,
    print ' '.join(servers)

def list_all_servers():
    hosts = HostMap().map
    print
    print 'Available servers:'
    print
    for hostname in hosts.keys():
        host = hosts[hostname]
        servers = [s.server_type for s in host.servers.values() if s.option.bootable]
        if servers:
            print '%s: %s' % (hostname, ' '.join(servers))

def check_local_server(server_type):
    hosts = HostMap().map
    hostname = get_hostname()
    if not hosts.has_key(hostname):
        print 'ERROR: host %s not found!' % hostname
        return None
    host = hosts[hostname]
    if not host.servers.has_key(server_type):
        print 'ERROR: server %s@%s not found!' % (server_type, hostname)
        return None
    return host.servers[server_type]

def check_env(name):
    envs = SystemEnv()
    v = envs.getEnv(name)
    if v is None:
        print 'ERROR: env $%s not found!' % name
        sys.exit(1)
    else:
        return v

def mkdir_if_absent(dir_):
    if not isdir(dir_):
        setting = GlobalSetting()
        debug('makedirs %s' % dir_)
        makedirs(dir_)

def search_command(name):
    paths = check_env('PATH')
    for dir_ in paths.split(os.pathsep):
        command = path.join(dir_, name)
        # os.stat()[0] return t_mode
        # S_IXUSR    00100     owner has execute permission
        if path.isfile(command) and os.stat(command)[0] & stat.S_IXUSR:
            return command
    return None

def get_java_exe():
    return path.join(check_env('JAVA_HOME'), 'bin', 'java')

def get_log_file(server_type):
    log_home = check_env('JAVA_LOG_HOME')
    mkdir_if_absent(log_home)
    return path.join(log_home, '%s-%s.log' % (server_type, get_hostname()))

class JavaExecutor:
    def __init__(self, server_define):
        self.server_define = server_define
        self.action_map = {'start':self.start_server, 'stop':self.stop_server, \
                           'restart':self.restart_server, 'status':self.server_status}
    def execute(self, action):
        handler = self.action_map[action]
        handler()

    def get_config_file(self):
        setting = GlobalSetting()
        return setting.config_file

    def get_pid_file(self, server_type):
        pid_home = check_env('JAVA_PID_HOME')
        mkdir_if_absent(pid_home)
        return path.join(pid_home, '%s-%s.pid' % (server_type, get_hostname()))
    
    def get_rotatelogs_script(self):
        return path.join(dirname(sys.argv[0]), 'rotatelogs.py')

    def start_server(self):
        configs = ConfigProperty()
        server_define = self.server_define
        server_type = server_define.server_type
        option = server_define.option.java_option
        hostname = get_hostname()
        
        pid_file = self.get_pid_file(server_type)

        pid = get_pid_by_file(pid_file)
        if pid is not None and find_pid(pid):
            print 'The server is running, use restart instead'
            return

        osid = configs.getProperty('osid')
        
        exe_supervisor = option.supervisor.build_option()
        if not isfile(exe_supervisor) and osid != 'win':
            print 'Supervisor not found:', exe_supervisor
            return
        
        if not hasattr(option, 'debug'):
            if not hasattr(server_define, 'server_port') or server_define.server_port is None:
                print 'Java Server(%s) Port not set!' % server_define.server_type
            else:
                server_port = int(server_define.server_port)
                if server_port <= 4000:
                    print 'Java Server Port(%s) is less than 4000, debug port will not set automatic' % server_define.server_port
                else:
                    debug_port = server_port - 4000
                    debug_option = JavaOptionDebug()
                    debug_option.port = str(debug_port)
                    setattr(option, 'debug', debug_option)

        if osid != 'win':
            command = '%s %s %s -cp "%s" %s %s start %s %s %s' % \
                      (exe_supervisor, option.user.build_option(), option.get_java_exe(), \
                       option.get_cp(), option.get_opts(), option.get_launcher_class(), \
                       self.get_config_file(), server_type, hostname)

            if hasattr(option, 'rotatelogs'):
                python_bin = search_command('python2') or search_command('python')
                rotatelogs = self.get_rotatelogs_script()
                log_pattern = option.rotatelogs.pattern
                log_pattern = log_pattern.replace('%n', server_type)
                log_pattern = log_pattern.replace('%o', hostname)
                cmd_start = '%s %s %s %s %s >> /tmp/rotatelogs.log 2>&1 &' % (python_bin, rotatelogs, pid_file,
                                                   log_pattern, command)
                run_by_shell(cmd_start)
            else:
                log_file = get_log_file(server_type)
                cmd_start = '%s >> %s 2>&1 &' % (command, log_file)
                cmd_pid = 'echo $! > %s' % pid_file
                run_by_shell(cmd_start, cmd_pid)
        else:
            command = '%s -cp "%s" %s %s start %s %s %s' % \
                      (option.get_java_exe(), \
                       option.get_cp(), option.get_opts(), option.get_launcher_class(), \
                       self.get_config_file(), server_type, hostname)

            debug('command: %s' % command)
            os.system('start %s' % command)
            
        print '[launcher  ] INFO : The server is started.'

    def stop_server(self):
        configs = ConfigProperty()
        osid = configs.getProperty('osid')
        
        server_define = self.server_define
        server_type = server_define.server_type
        option = server_define.option.java_option
        hostname = get_hostname()

        command = '%s -cp "%s" %s stop %s %s %s' % \
                  (option.get_java_exe(), option.get_cp(), option.get_launcher_class(), \
                   self.get_config_file(), server_type, hostname)

        if osid != 'win':
            run_by_shell(command)
        else:
            os.system(command)
        
        pid_file= self.get_pid_file(server_type)
        pid = get_pid_by_file(pid_file)
        if pid is not None:
            if kill_proc(pid) and path.exists(pid_file):
                os.unlink(pid_file)

    def restart_server(self):
        self.stop_server()
        sleep(1)
        self.start_server()

    def server_status(self):
        server_define = self.server_define
        server_type = server_define.server_type
        pid_file= self.get_pid_file(server_type)
        pid = get_pid_by_file(pid_file)
        if pid is None:
            print '%s is stopped' % server_type
        elif find_pid(pid):
            print '%s (pid %s) is running...' % (server_type, pid)
        else:
            print '%s dead but pid file exists' % server_type

def perform(action, server_define):
    boot_type = server_define.option.boot_type
    if boot_type == BootOption.BOOT_TYPE_SHELL:
        system('%s %s' % (server_define.option.shell_option.command, action))
    elif boot_type == BootOption.BOOT_TYPE_JAVA:
        executor = JavaExecutor(server_define)
        executor.execute(action)

class BackupExecutor:
    def __init__(self, argv):
        self.compress_mode = False
        self.backup_home = check_env('BACKUP_HOME')

        opts, args = getopt.getopt(argv, 'cd:m:')
        if len(args) <= 0:
            show_usage()

        self.args = args
        
        for o, a in opts:
            if o == '-c':
                self.compress_mode = True
            elif o == '-d':
                self.backup_home = a
            elif o == '-m':
                self.comment = a

    def execute(self):
        setting = GlobalSetting()
        
        timestr = strftime('%Y-%m-%d', localtime())
        bakdir = path.join(self.backup_home, timestr)
        mkdir_if_absent(bakdir)

        actions = []
        
        for filename in self.args:
            if not path.exists(filename):
                print '%s not exists!' % filename
                continue
            destfile = self.get_filename(bakdir, filename)
            if destfile is None:
                print 'Cannot get destination filename of %s' % filename
                continue
            cmd = ''
            if path.isdir(filename):
                if self.compress_mode:
                    cmd = 'tar cf - %s | gzip > %s' % (filename, destfile)
                else:
                    cmd = 'tar cf %s %s' % (destfile, filename)
            else:
                if self.compress_mode:
                    cmd = 'gzip -c %s > %s' % (filename, destfile)
                else:
                    cmd = 'cp %s %s' % (filename, destfile)

            debug(cmd)

            actions.append(cmd)
            print cmd
            system(cmd)

        logtime = strftime('%Y-%m-%d %H:%M:%S', localtime())
        hostname = get_local_hostname()
        cwd = path.realpath(path.os.curdir)
        fp = open(path.join(self.backup_home, 'backup.log'), 'a')
        fp.writelines(['%s [%s] %s' % (logtime, hostname, cwd)])
        fp.write(os.linesep)
        fp.write(os.linesep.join(actions))
        fp.write(os.linesep)
        fp.write(os.linesep)
        fp.flush()
        fp.close()
            
    def get_filename(self, bakdir, pathname):
        suffix = ''
        if path.isdir(pathname):
            suffix += '.tar'
        if self.compress_mode:
            suffix += '.gz'

        filename = pathname.replace(path.os.sep, '_')
        if not path.exists(path.join(bakdir, filename + suffix)):
            return path.join(bakdir, filename + suffix)

        no = 1
        while no < 10000:
            fullpath = path.join(bakdir, '%s.%s%s' % (filename, str(no), suffix))
            if not path.exists(fullpath):
                return fullpath
            no += 1

        return None

def list_all_jars():
    jars = []
    servers = ServerMap()
    for server_define in servers.map.values():
        java_option = server_define.option.java_option
        cps = []
        cps.extend(java_option.classpaths)
        cps.extend(java_option.boot_classpaths)
        cps.extend(server_define.classpaths)
        for cp in cps:
            for classpath in cp.get_files():
                if (classpath.endswith('.jar') or classpath.endswith('.zip')) and isfile(classpath) and classpath not in jars:
                    jars.append(classpath)
    return jars

class JarSummaryBase:
    def __init__(self, summary_file):
        self.summary_file = summary_file
        self.sums = {}
        self.read_summaries()
    def read_summaries(self):
        sum_file = self.summary_file
        if not isfile(sum_file):
            return

        fp = open(sum_file, 'r')
        lines = fp.readlines()
        fp.close()

        for line in lines:
            if not line:
                continue
            if line.find(',') < 0:
                continue
            mtime, jar = string.split(line, ',', 1)
            if not jar:
                continue
            jar = jar.strip()
            self.sums[jar] = int(mtime)

    def save_summaries(self):
        fp = open(self.summary_file, 'w')
        for jar, mtime in self.sums.iteritems():
            fp.write('%s,%s' % (str(mtime), jar))
            fp.write(os.linesep)
            fp.flush()
        fp.close()

    def get_mtime(self, jar):
        return os.stat(jar)[8]

    def is_modified(self, jar):
        if not self.sums.has_key(jar):
            return True
        mtime = self.sums[jar]
        return self.get_mtime(jar) > mtime

class ClassLocator(JarSummaryBase):
    def __init__(self):
        user_home = get_userhome()
        self.cache_dir = path.join(user_home, '.adf', 'classcaches')
        mkdir_if_absent(self.cache_dir)
        JarSummaryBase.__init__(self, path.join(self.cache_dir, 'summary'))

        self.jars = list_all_jars()

    def get_index_file(self, jar):
        return path.join(self.cache_dir, jar.replace(path.os.sep, '_') + '.idx')

    def get_jar_content(self, jar):
        jarfile = ZipFile(jar)
        file_list = jarfile.namelist()
        jarfile.close()
        return file_list

    def build_indices(self):
        for jar in self.jars:
            index_file = self.get_index_file(jar)
            if path.exists(index_file) and os.stat(index_file)[6] > 0 and not self.is_modified(jar):
                continue
            print strftime('[%Y-%m-%d %H:%M]', localtime()),
            print 'building index of %s' % jar
            classes = self.get_jar_content(jar)
            fp = open(index_file, 'w')
            for cls in classes:
                fp.write(cls + os.linesep)
            fp.close()
            self.sums[jar] = self.get_mtime(jar)
            self.save_summaries()

    def find(self, keyword):
        self.build_indices()
        key = re.compile(keyword, re.I)

        for jar in self.jars:
            index_file = self.get_index_file(jar)
            if not isfile(index_file):
                continue

            matches = []
            fp = open(index_file, 'r')
            while True:
                line = fp.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                if key.search(line) is not None:
                    matches.append(line)
            fp.close()

            if len(matches) > 0:
                print jar + ':'
                for line in matches:
                    print '  ' + line
                print

class CommandLocator:
    class JarFileInfo:
        def __init__(self):
            self.entities = {}
        
        def __str__(self):
            return str_object(self, ('name', 'entities'))
        
        def parse(self, e):
            self.name = get_attribute(e, 'name', True)
            self.mtime = int(get_attribute(e, 'last-modified', True))
            
            if self.is_modified():
                self.rebuild()
                return
            
            for entity_e in list_child_elements(e, 'entity'):
                entity = CommandLocator.EntityInfo()
                entity.parse(entity_e)
                self.entities[entity.name] = entity
            
        def is_modified(self):
            return os.stat(self.name)[8] > self.mtime
        
        def rebuild(self):
            self.mtime = os.stat(self.name)[8]
            jar = ZipFile(self.name)
            for name in jar.namelist():
                if name.endswith('.xml'):
                    print 'parsing %s ...' % name
                    content = jar.read(name)
                    entity = self.build_xml_entity(name, content)
                    if entity:
                        self.entities[name] = entity
                elif name.endswith('/modules.properties') or name.endswith('/models.properties'):
                    print 'parsing %s ...' % name
                    content = jar.read(name)
                    entity = self.build_prop_entity(name, content)
                    if entity:
                        self.entities[name] = entity
            jar.close()
        
        def build_xml_entity(self, name, content):
            doc = get_doc_by_string(content)
            if doc is None:
                return
            root = doc.documentElement
            nas_e = get_first_child_element(root, 'nas')
            if nas_e is None:
                return None
            services_e = get_first_child_element(nas_e, 'services')
            if services_e is None:
                return None
            
            entity = CommandLocator.EntityInfo()
            entity.name = name
            
            for service_e in list_child_elements(services_e, 'service'):
                service_name = get_attribute(service_e, 'name', True)
                models_e = get_first_child_element(service_e, 'models')
                if models_e is None:
                    models_e = get_first_child_element(service_e, 'modules')
                if models_e is None:
                    continue
                models_array = list_child_elements(models_e, 'model') + list_child_elements(models_e, 'module')
                for model_e in models_array:
                    if model_e.hasAttribute('name') and model_e.hasAttribute('class'):
                        cmd = CommandLocator.CommandInfo()
                        cmd.service = service_name
                        fetch_attrs(cmd, model_e, ('name', 'class', True))
                        entity.cmds.append(cmd)
            
            return entity
        
        def build_prop_entity(self, name, content):
            if not content:
                return None
            
            entity = CommandLocator.EntityInfo()
            entity.name = name
            
            for line in re.split('[\\r\\n]+', content):
                result = re.match('(.+)=(.+)', line)
                if result:
                    name = result.group(1)
                    klass = result.group(2)
                    cmd = CommandLocator.CommandInfo()
                    setattr(cmd, 'name', name)
                    setattr(cmd, 'class', klass)
                    entity.cmds.append(cmd)
            
            return entity
    
    class EntityInfo:
        def __init__(self):
            self.cmds = []
        
        def __str__(self):
            return str_object(self, ('name', 'cmds'))
        
        def parse(self, e):
            self.name = get_attribute(e, 'name', True)
            for cmd_e in list_child_elements(e, 'cmd'):
                cmd = CommandLocator.CommandInfo()
                cmd.parse(cmd_e)
                self.cmds.append(cmd)
    
    class CommandInfo:
        def __str__(self):
            return str_object(self, ('name', 'class', 'service'))
        
        def parse(self, e):
            fetch_attrs(self, e, ('name', 'class'), True)
            fetch_attrs(self, e, ('service',))
    
    def __init__(self):
        user_home = get_userhome()
        cache_dir = path.join(user_home, '.adf')
        mkdir_if_absent(cache_dir)
        self.index_file = path.join(cache_dir, 'cmdcaches.xml')
        
        self.jarfiles = {}
        self.read_cache()
        
        for jar in list_all_jars():
            if not self.jarfiles.has_key(jar):
                print strftime('[%Y-%m-%d %H:%M]', localtime()),
                print 'building index of %s' % jar
                jarfile = CommandLocator.JarFileInfo()
                jarfile.name = jar
                jarfile.rebuild()
                self.jarfiles[jar] = jarfile
        
        self.save_cache()
    
    def __str__(self):
        return str_object(self, ('jarfiles',))
    
    def read_cache(self):
        if not path.exists(self.index_file):
            return
        doc = minidom.parse(self.index_file)
        root = doc.documentElement
        for jar_file_e in list_child_elements(root, 'jar-file'):
            jarfile = CommandLocator.JarFileInfo()
            try:
                jarfile.parse(jar_file_e)
                self.jarfiles[jarfile.name] = jarfile
            except OSError:
                debug('cached jar file not found: %s' % jarfile.name)
    
    def save_cache(self):
        impl = minidom.getDOMImplementation()
        doc = impl.createDocument(None, 'cmd-cache', None)
        root = doc.documentElement
        
        for jarfile in self.jarfiles.values():
            jar_file_e = doc.createElement('jar-file')
            root.appendChild(jar_file_e)
            
            jar_file_e.setAttribute('name', jarfile.name)
            jar_file_e.setAttribute('last-modified', str(jarfile.mtime))
            
            for entity in jarfile.entities.values():
                entity_e = doc.createElement('entity')
                jar_file_e.appendChild(entity_e)
                
                entity_e.setAttribute('name', entity.name)
                
                for cmd in entity.cmds:
                    cmd_e = doc.createElement('cmd')
                    entity_e.appendChild(cmd_e)
                    
                    cmd_e.setAttribute('name', cmd.name)
                    cmd_e.setAttribute('class', getattr(cmd, 'class'))
                    if hasattr(cmd, 'service'):
                        cmd_e.setAttribute('service', cmd.service)
        
        fp = open(self.index_file, 'w')
        doc.writexml(fp, '', '  ', os.linesep)
        fp.close()
    
    def find(self, keyword):
        re_key = re.compile(keyword, re.I)
        for jarfile in self.jarfiles.values():
            for entity in jarfile.entities.values():
                matches = []
                for cmd in entity.cmds:
                    if re_key.search(cmd.name) is not None:
                        matches.append(cmd)
                if len(matches) > 0:
                    print '%s!%s:' % (jarfile.name, entity.name)
                    for cmd in matches:
                        print ' ',
                        if hasattr(cmd, 'service'):
                            print 'service[%s]' % cmd.service,
                        print '%s = %s' % (cmd.name, getattr(cmd, 'class'))
                    print

class PropertyLocator(JarSummaryBase):
    def __init__(self):
        user_home = get_userhome()
        self.cache_dir = path.join(user_home, '.adf', 'propcaches')
        mkdir_if_absent(self.cache_dir)
        JarSummaryBase.__init__(self, path.join(self.cache_dir, 'summary'))
        self.jars = list_all_jars()
        
    def get_index_file(self, jar, entity_name):
        filename = '%s!%s' % (jar.replace(path.os.sep, '_'), entity_name.replace('/', '_'))
        return path.join(self.cache_dir, filename)
    
    def build_indices(self):
        for jar in self.jars:
            if not self.is_modified(jar):
                continue
            print strftime('[%Y-%m-%d %H:%M]', localtime()),
            print 'parsing %s ...' % jar
            jarfile = ZipFile(jar)
            for name in jarfile.namelist():
                if name.endswith('.properties'):
                    content = jarfile.read(name)
                    index_file = self.get_index_file(jar, name)
                    fp = open(index_file, 'w')
                    fp.write(content)
                    fp.close()
            jarfile.close()
            self.sums[jar] = self.get_mtime(jar)
            self.save_summaries()
    
    def find(self, keyword):
        self.build_indices()
        re_key = re.compile(keyword, re.I)
        for jar in self.jars:
            jarfile = ZipFile(jar)
            for name in jarfile.namelist():
                if name.endswith('.properties'):
                    index_file = self.get_index_file(jar, name)
                    if path.exists(index_file):
                        matches = []
                        fp = open(index_file, 'r')
                        while True:
                            line = fp.readline()
                            if not line:
                                break
                            line = line.strip()
                            if not line:
                                continue
                            if re_key.search(line) is not None:
                                matches.append(line)
                        fp.close()
                        
                        if len(matches) > 0:
                            print '%s!%s:' % (jar, name)
                            for line in matches:
                                print ' ', line
                            print
            jarfile.close()

class LogViewer:
    
    def execute(self, server_define):
        if server_define.option.boot_type != BootOption.BOOT_TYPE_JAVA:
            print 'Only java server supports logview'
            return
        
        option = server_define.option.java_option
        server_type = server_define.server_type
        filename = None
        if hasattr(option, 'rotatelogs'):
            log_pattern = option.rotatelogs.pattern
            log_pattern = log_pattern.replace('%n', server_type)
            log_pattern = log_pattern.replace('%o', get_hostname())
            filename = strftime(log_pattern, localtime())
        else:
            filename = get_log_file(server_type)
        
        self.perform(filename)
        
    def perform(self, filename):
        system('tail -f %s' % filename)

class LogEditor(LogViewer):
    def perform(self, filename):
        system('vi -R %s' % filename)

def get_osid():
    osinfo = platform.uname()
    system_name = string.lower(osinfo[0])
    if system_name in ('hp-ux', 'hpux'):
        return 'hpux'
    if system_name in ('sunos', 'solaris'):
        processor = string.lower(osinfo[-1])
        if processor == 'i386':
            return 'sunosx86'
        else:
            return 'sunos'
    if system_name in ('nt', 'windows'):
        return 'win'
    return system_name

def show_usage():
    setting = GlobalSetting()
    script_name = setting.script_name
    if script_name is None:
        app_name = basename(sys.argv[0])
        # ADF_SCRIPT_NAME should set to product control script name.
        # ie: umail, smg, imeg ...
        envs = SystemEnv()
        script_name = envs.getEnv('ADF_SCRIPT_NAME', app_name)
    else:
        script_name = basename(script_name)

    app = (script_name,)
    usage_message = '''
Usage: %s (start|stop|restart|status) server1 server2 ...
       %s (start|stop|restart|status) all
       %s server1 server2 ... (start|stop|restart|status)
       %s all (start|stop|restart|status)
       %s list
       %s listall
       %s log server1 server2 ...
       %s loge servername
       %s bak [option] file1 file2 ...
       %s class keyword
       %s cmd keyword
       %s prop keyword
       %s version
       %s version jar1 jar2 ...
       %s help

    start   - start server
    stop    - stop server
    restart - restart server
    status  - dump the status message

    list    - list available servers in current host
    listall - list all servers
    log     - view JAVA server's log
    loge    - edit one JAVA server's log file
    bak     - backup files
    class   - find classes
    cmd     - find command defination
    prop    - search in properties files
    version - print jar version messages; If no jar-name is given, the
              product version message will be print, which is defined in config
              file as system env: PRODUCT_NAME, PRODUCT_VERSION
    help    - print this help message

Options:
  -c <config> specify the config file
  -d      enable java remote debug
  -v      verbose mode
  -h      specify the hostname

Backup options:
  -c      compress mode
  -d      change backup home
  -m      add comments
'''
    print usage_message % (app * 15)
    sys.exit(0)

def show_product_version():
    product_home = dirname(dirname(sys.argv[0]))
    version_file = path.join(product_home, 'version.txt')
    if isfile(version_file):
        f = open(version_file)
        try:
            print f.read()
        finally:
            f.close()
    else:
        show_product_version_fromenv()

def show_product_version_fromenv():
    envs = SystemEnv()
    product_name = envs.getEnv('PRODUCT_NAME')
    product_version = envs.getEnv('PRODUCT_VERSION')
    if product_name is None and product_version is None:
        print 'There is no version info'
    else:
        versions = []
        if product_name is not None: versions.append(product_name)
        if product_version is not None: versions.append(product_version)
        print string.join(versions, '-')

def show_jar_version(jar_names):
    for jar in list_all_jars():
        for jar_name in jar_names:
            if basename(jar) == jar_name:
                print 'Version of %s:' % jar

                jar_file = ZipFile(jar)
                file_list = jar_file.namelist()
                if file_list.count('VersionView.class') > 0:
                    java_exe = get_java_exe()
                    cmd = '%s -jar %s' % (java_exe, jar)
                    os.system(cmd)
                else:
                    content = jar_file.read('META-INF/MANIFEST.MF')
                    print content
                jar_file.close()
                print

def check_python_version():
    version = string.split(string.split(sys.version)[0], '.')
    if map(int, version[:2]) < [2, 4]:
        print 'This script require Python "2.4" or above, current version is', sys.version
        sys.exit(1)

if __name__ == '__main__':
    check_python_version()

    setting = GlobalSetting()
    envs = SystemEnv()
    configs = ConfigProperty()

    configs.setProperty('osid', get_osid())

    opts, args = getopt.getopt(sys.argv[1:], 'c:n:vdh:')
    argc = len(args)

    config_file = ''
    for o, a in opts:
        if o == '-c':
            config_file = a
        elif o == '-d':
            setting.java_debug_mode = True
        elif o == '-v':
            setting.verbose_mode = True
        elif o == '-n':
            setting.script_name = a
        elif o == '-h':
            setting.hostname = a

    if envs.getEnv('REMOTE_JAVA_DEBUG') == 'on':
        setting.java_debug_mode = True

    if not config_file:
        show_usage()

    setting.config_file = config_file

    parse_config(config_file)
    merge_options()

    if argc == 0:
        show_usage()

    command = args[0]

    last_word = args[-1]
    if argc > 1 and last_word in ('start', 'stop', 'restart', 'status'):
        args.pop()
        args.insert(0, last_word)
        command = last_word

    if command == 'list':
        list_local_servers()

    elif command == 'listall':
        list_all_servers()

    elif command in ('start', 'stop', 'restart', 'status'):
        server_type_list = None

        if argc == 1 and command == 'status':
            server_type_list = ['all']
        elif argc >= 2:
            server_type_list = args[1:]
        elif argc < 2:
            show_usage()

        if 'all' in server_type_list:
            server_type_list = get_local_servers()

        for server_type in server_type_list:
            server_define = check_local_server(server_type)
            if server_define is None:
                continue
            print 'try to %s %s ...' % (command, server_type)
            perform(command, server_define)

    elif command in ('log', 'loge'):
        if argc < 2:
            show_usage()

        server_type = args[1]
        server_define = check_local_server(server_type)
        if server_define is not None:
            if command == 'log':
                viewer = LogViewer()
            else:
                viewer = LogEditor()
            viewer.execute(server_define)

    elif command in ('bak', 'backup'):
        if argc < 2:
            show_usage()

        backup = BackupExecutor(args[1:])
        backup.execute()

    elif command == 'class':
        if argc < 2:
            show_usage()

        locator = ClassLocator()
        locator.find(args[1])

    elif command == 'cmd':
        if argc < 2:
            show_usage()

        locator = CommandLocator()
        locator.find(args[1])

    elif command == 'prop':
        if argc < 2:
            show_usage()

        locator = PropertyLocator()
        locator.find(args[1])
    
    elif command == 'version':
        if argc < 2:
            show_product_version()
        else:
            show_jar_version(args[1:])
    
    else:
        show_usage()
