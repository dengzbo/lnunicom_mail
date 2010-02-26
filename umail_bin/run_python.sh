#!/bin/sh
#
# 2006/10/30 Bug-Fix CENOADF-8
#

script=`echo $@ | awk '{print $1}'`
argv=`echo $@ | sed 's/^ *[a-zA-Z0-9_\/\.\-]* *\(.*\)/\1/g'`

paths=`echo $PATH | tr ':' ' '`
paths="$paths /usr/local/bin /usr/bin"

for search_dir in $paths; do
    for script_name in 'python2' 'python'; do
        if [ -x "$search_dir/$script_name" ]; then
            python_bin="$search_dir/$script_name"
            break
        fi
    done
    test $python_bin && break
done

if [ -z "$python_bin" ] ; then
    echo Cannot find python script in $PATH
    exit 1
fi

if [ ! -f $script ]; then
    echo "File not found: $script"
    exit 1
fi

$python_bin $script $argv