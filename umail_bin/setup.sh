#!/bin/sh

groupadd -g 1818  ares
useradd  -g 1818 -u 1818   ares

if [ "$CENO_HOME" = "" ]; then
    echo "Can't find CENO_HOME , Please add /ceno/product/umail/etc/profile to /etc/profile"
    exit
fi

if [ "$UMAIL_HOME" = "" ]; then
    echo "Can't find UMAIL_HOME, Please add /ceno/product/umail/etc/profile to /etc/profile"
    exit
fi

mkdir -p $CENO_HOME/journal/umail

chown ares:ares $CENO_HOME
chown -R ares:ares $UMAIL_HOME/report
chown -R ares:ares $UMAIL_HOME/temp
chown -R ares:ares $UMAIL_HOME/log
chown -R ares:ares $UMAIL_HOME/var
chown -R ares:ares $UMAIL_HOME/web
chown -R ares:ares $UMAIL_HOME/sql
chown -R ares:ares $UMAIL_HOME/api
chown -R ares:ares $UMAIL_HOME/pimapd
chown -R ares:ares $UMAIL_HOME/push
chown -R ares:ares $UMAIL_HOME/tomcat
chmod -R 775 $UMAIL_HOME/lib/native/*
chmod -R 775 $UMAIL_HOME/bin/*

. $UMAIL_HOME/bin/mkqueue.sh
. $UMAIL_HOME/push/bin/mkq-push.sh

