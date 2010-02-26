#!/bin/sh

groupadd -g 1818  ares
useradd  -g 1818 -u 1818   ares

if [ "$1" = "" ];then
 echo "  Usage:"
 echo "       localsetup.sh product sharing path"
 echo "  Example:"
 echo "       localsetup.sh /email/share/ceno/product"
 exit
fi
       
SHARE_PRODUCT_HOME=$1
CENO_HOME=/ceno
JDK_HOME=$CENO_HOME/product/jdk
TOMCAT_HOME=$CENO_HOME/product/tomcat
UMAIL_HOME=$CENO_HOME/product/umail
UMAIL_JOURNAL=$CENO_HOME/journal/umail

mkdir  -p $UMAIL_HOME
mkdir  -p $UMAIL_JOURNAL
ln -s $SHARE_PRODUCT_HOME/umail/bin     $UMAIL_HOME/bin
ln -s $SHARE_PRODUCT_HOME/umail/conf    $UMAIL_HOME/conf
ln -s $SHARE_PRODUCT_HOME/umail/lib     $UMAIL_HOME/lib
ln -s $SHARE_PRODUCT_HOME/umail/web     $UMAIL_HOME/web
ln -s $SHARE_PRODUCT_HOME/umail/ibis    $UMAIL_HOME/ibis
ln -s $SHARE_PRODUCT_HOME/umail/report  $UMAIL_HOME/report
ln -s $SHARE_PRODUCT_HOME/umail/patch   $UMAIL_HOME/patch
ln -s $SHARE_PRODUCT_HOME/umail/sql     $UMAIL_HOME/sql
ln -s $SHARE_PRODUCT_HOME/umail/temp    $UMAIL_HOME/temp
ln -s $SHARE_PRODUCT_HOME/umail/api     $UMAIL_HOME/api
ln -s $SHARE_PRODUCT_HOME/umail/pimapd  $UMAIL_HOME/pimapd
ln -s $SHARE_PRODUCT_HOME/umail/push    $UMAIL_HOME/push
ln -s $SHARE_PRODUCT_HOME/umail/tomcat  $UMAIL_HOME/tomcat
ln -s $SHARE_PRODUCT_HOME/jdk		$JDK_HOME
ln -s $SHARE_PRODUCT_HOME/tomcat	$TOMCAT_HOME

mkdir $UMAIL_HOME/log
mkdir $UMAIL_HOME/var
mkdir $UMAIL_HOME/queue

cp -rf $SHARE_PRODUCT_HOME/umail/etc $UMAIL_HOME/etc

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

export JAVA_HOME=$JDK_HOME
export PATH=$JAVA_HOME/bin:$PATH
. mkqueue.sh
. $UMAIL_HOME/push/bin/mkq-push.sh
