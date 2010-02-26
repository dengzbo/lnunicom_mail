#!/usr/bin/env python2
# -*- coding: UTF-8 -*-

import unittest

from adfctl import *

class TestMergeAttrs(unittest.TestCase):
    class C:
        pass
    def test_attrfrom_not_exists(self):
        cfrom = self.C()
        cto = self.C()
        merge_attrs(cfrom, cto, ['name'])
        self.assertFalse(hasattr(cto, 'name'))

        name = 'value'
        cto.name = name
        merge_attrs(cfrom, cto, ['name'])
        self.assertTrue(hasattr(cto, 'name'))
        self.assertEquals(cto.name, name)
    def test_attrfrom_exists_and_attrto_not_exists(self):
        cfrom = self.C()
        cto = self.C()
        name = 'value'
        cfrom.name = name
        merge_attrs(cfrom, cto, ['name'])
        self.assertTrue(hasattr(cto, 'name'))
        self.assertEquals(cto.name, name)
    def test_both_attrfrom_and_attrto_exists(self):
        cfrom = self.C()
        cto = self.C()
        fromvalue = 'fromvalue'
        cfrom.name = fromvalue
        tovalue = 'tovalue'
        cto.name = tovalue
        merge_attrs(cfrom, cto, ['name'])
        self.assertEquals(cto.name, tovalue)
    def test_array_attrs(self):
        cfrom = self.C()
        cto = self.C()
        cfrom.a = (1, 2, 3)
        cto.a = [4, 5]
        merge_attrs(cfrom, cto, ['a'])
        self.assertTrue(len(cto.a) == 5)
        self.assertEquals(cto.a[0], 1)
        self.assertEquals(cto.a[1], 2)
        self.assertEquals(cto.a[2], 3)
        self.assertEquals(cto.a[3], 4)
        self.assertEquals(cto.a[4], 5)
    def test_array_from_not_exists(self):
        cfrom = self.C()
        cto = self.C()
        cto.a = [1, 2]
        merge_attrs(cfrom, cto, ['a'])
        self.assertEquals(cto.a, [1, 2])
    def test_array_to_not_exists(self):
        cfrom = self.C()
        cto = self.C()
        cfrom.a = [1, 2]
        merge_attrs(cfrom, cto, ['a'])
        self.assertEquals(cto.a, [1, 2])

class TestStrObject(unittest.TestCase):
    class A:
        def __init__(self):
            self.name = 'name'
            self.value = 'value'
        def __str__(self):
            return str_object(self, ('name', 'value'))
    def testit(self):
        a = self.A()
        desc = str(a)
        self.assertEquals(desc[0], 'A')
        self.assertTrue(desc.find('name') > 0)
        self.assertTrue(desc.find('value') > 0)

class TestSingleton(unittest.TestCase):
    class OneSingleton(Singleton):
        def __init__(self):
            if self._is_initted():
                return
            if hasattr(self, 'count'):
                self.count = self.count + 1
            else:
                self.count = 1
    def testid(self):
        a = TestSingleton.OneSingleton()
        b = TestSingleton.OneSingleton()
        self.assertEquals(id(a), id(b))

    def testinit(self):
        c = TestSingleton.OneSingleton()
        d = TestSingleton.OneSingleton()
        self.assert_(c.count == 1)

class TestSystemEnv(unittest.TestCase):
    def testsingle(self):
        envs = SystemEnv()
        envs.setEnv('MY_VAR1', 'var1')
        self.assertEquals(envs.resolve('v is $MY_VAR1.'), 'v is var1.')
    def testdouble(self):
        envs = SystemEnv()
        envs.setEnv('MY_VAR1', 'var1')
        envs.setEnv('MY_VAR2', 'var2')
        self.assertEquals(envs.resolve('v1 is $MY_VAR1, and v2 is $MY_VAR2.'), 'v1 is var1, and v2 is var2.')

class TestConfigProperty(unittest.TestCase):
    def testsingle(self):
        props = ConfigProperty()
        props.setProperty('myvar1', 'var1')
        self.assertEquals(props.resolve('v1 is ${myvar1}.'), 'v1 is var1.')
    def testdouble(self):
        props = ConfigProperty()
        props.setProperty('myvar1', 'var1')
        props.setProperty('myvar2', 'var2')
        self.assertEquals(props.resolve('v1 is ${myvar1}, and v2 is ${myvar2}.'), 'v1 is var1, and v2 is var2.')

class TestJavaOption(unittest.TestCase):
    def new_full_option(self):
        option = JavaOption()
        option.supervisor = JavaOptionSupervisor()
        option.supervisor.base = '/ares/bin'
        option.supervisor.name = 'jnohup'

        option.user = JavaOptionUser()
        option.user.name = 'ares'

        option.memory = JavaOptionMemory()
        option.memory.min = '128m'
        option.memory.max = '128m'

        option.logger = JavaOptionLogger()
        option.logger.priority = 'INFO'

        option.debug = JavaOptionDebug()
        option.debug.port = '5001'

        bootcp1 = JavaOptionBootClasspath()
        bootcp1.file = '/ares/lib/ceno-base.jar'
        bootcp2 = JavaOptionBootClasspath()
        bootcp2.file = '/ares/lib/framework.jar'
        option.boot_classpaths.append(bootcp1)
        option.boot_classpaths.append(bootcp2)

        cp1 = JavaOptionClasspath()
        cp1.file = '/ares/lib/ceno-modules.jar'
        cp2 = JavaOptionClasspath()
        cp2.file = '/ares/lib/j2ee.jar'
        option.classpaths.append(cp1)
        option.classpaths.append(cp2)

        prop1 = JavaOptionProperty()
        prop1.name = 'ibis.home'
        prop1.value = '/ares/ibis'
        prop2 = JavaOptionProperty()
        prop2.name = 'umta.home'
        prop2.value = '/ares/umta'
        option.props.append(prop1)
        option.props.append(prop2)

        return option

    def test_fromisempty_toisfull(self):
        emptyoption = JavaOption()
        prop = JavaOptionProperty()
        prop.name = 'home'
        prop.value = '/ares'
        emptyoption.props.append(prop)
        
        fulloption = self.new_full_option()
        newoption = copy.deepcopy(fulloption)
        emptyoption.merge_to(newoption)

        self.assertTrue(hasattr(newoption, 'supervisor'))
        self.assertTrue(hasattr(newoption.supervisor, 'base'))
        self.assertTrue(hasattr(newoption.supervisor, 'name'))

        self.assertTrue(hasattr(newoption, 'user'))
        self.assertTrue(hasattr(newoption.user, 'name'))

        self.assertTrue(hasattr(newoption, 'memory'))
        self.assertTrue(hasattr(newoption.memory, 'min'))
        self.assertTrue(hasattr(newoption.memory, 'max'))

        self.assertTrue(hasattr(newoption, 'logger'))
        self.assertTrue(hasattr(newoption.logger, 'priority'))

        self.assertTrue(hasattr(newoption, 'debug'))
        self.assertTrue(hasattr(newoption.debug, 'port'))

        self.assertTrue(len(newoption.boot_classpaths) == 2)
        self.assertTrue(len(newoption.classpaths) == 2)
        self.assertTrue(len(newoption.props) == 3)

        prophome = newoption.props[0]
        self.assertEquals(prophome.name, 'home')
        self.assertEquals(prophome.value, '/ares')

    def test_fromisfull_toisempty(self):
        emptyoption = JavaOption()
        memory = JavaOptionMemory()
        memory.min = '256m'
        memory.max = '256m'
        emptyoption.memory = memory

        fulloption = self.new_full_option()
        newoption = copy.deepcopy(emptyoption)
        fulloption.merge_to(newoption)

        self.assertTrue(hasattr(newoption, 'supervisor'))
        self.assertTrue(hasattr(newoption.supervisor, 'base'))
        self.assertTrue(hasattr(newoption.supervisor, 'name'))

        self.assertTrue(hasattr(newoption, 'user'))
        self.assertTrue(hasattr(newoption.user, 'name'))

        self.assertTrue(hasattr(newoption, 'memory'))
        self.assertTrue(hasattr(newoption.memory, 'min'))
        self.assertEquals(newoption.memory.min, '256m')
        self.assertTrue(hasattr(newoption.memory, 'max'))
        self.assertEquals(newoption.memory.max, '256m')

        self.assertTrue(hasattr(newoption, 'logger'))
        self.assertTrue(hasattr(newoption.logger, 'priority'))

        self.assertTrue(hasattr(newoption, 'debug'))
        self.assertTrue(hasattr(newoption.debug, 'port'))

        self.assertTrue(len(newoption.boot_classpaths) == 2)
        self.assertTrue(len(newoption.classpaths) == 2)
        self.assertTrue(len(newoption.props) == 2)

class TestBootOption(unittest.TestCase):
    def test_merge_bootable(self):
        b1 = BootOption()
        b2 = BootOption()

        b1.bootable = False
        b2.bootable = True
        b1.merge_to(b2)
        self.assertEquals(b2.bootable, False)

        b1.bootable = True
        b2.bootable = False
        b1.merge_to(b2)
        self.assertEquals(b2.bootable, False)

        b1.bootable = True
        b2.bootable = True
        b1.merge_to(b2)
        self.assertEquals(b2.bootable, True)

        b1.bootable = False
        b2.bootable = False
        b1.merge_to(b2)
        self.assertEquals(b2.bootable, False)

    def test_merge_boot_type(self):
        b1 = BootOption()
        b2 = BootOption()

        b1.boot_type = BootOption.BOOT_TYPE_JAVA
        b2.boot_type = BootOption.BOOT_TYPE_SHELL
        b1.merge_to(b2)
        self.assertEquals(b2.boot_type, BootOption.BOOT_TYPE_SHELL)

        b1.boot_type = BootOption.BOOT_TYPE_SHELL
        b2.boot_type = BootOption.BOOT_TYPE_JAVA
        b1.merge_to(b2)
        self.assertEquals(b2.boot_type, BootOption.BOOT_TYPE_SHELL)

        b1.boot_type = BootOption.BOOT_TYPE_JAVA
        b2.boot_type = BootOption.BOOT_TYPE_JAVA
        b1.merge_to(b2)
        self.assertEquals(b2.boot_type, BootOption.BOOT_TYPE_JAVA)

        b1.boot_type = BootOption.BOOT_TYPE_SHELL
        b2.boot_type = BootOption.BOOT_TYPE_SHELL
        b1.merge_to(b2)
        self.assertEquals(b2.boot_type, BootOption.BOOT_TYPE_SHELL)

    def test_merge_envs(self):
        b1 = BootOption()
        b2 = BootOption()

        b1.merge_to(b2)
        self.assertTrue(len(b2.envs) == 0)
        
        env1 = EnvSetting()
        env1.name = 'OS_DIR'
        env1.value = 'linux'

        env2 = EnvSetting()
        env2.name = 'TEMP_HOME'
        env2.value = '/ares/temp'

        b1.envs.append(env1)
        b1.merge_to(b2)
        self.assertTrue(len(b2.envs) == 1)
        self.assertEquals(b2.envs[0].name, 'OS_DIR')
        self.assertEquals(b2.envs[0].value, 'linux')

        b2.envs = [env2]
        b1.merge_to(b2)
        self.assertTrue(len(b2.envs) == 2)
        self.assertEquals(b2.envs[0].name, 'OS_DIR')
        self.assertEquals(b2.envs[0].value, 'linux')
        self.assertEquals(b2.envs[1].name, 'TEMP_HOME')
        self.assertEquals(b2.envs[1].value, '/ares/temp')

        b1.envs = []
        b2.envs = [env1]
        b1.merge_to(b2)
        self.assertTrue(len(b2.envs) == 1)

if __name__ == '__main__':
    unittest.main()
