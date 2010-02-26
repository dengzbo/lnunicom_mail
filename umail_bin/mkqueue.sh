JAVA_EXE=$JAVA_HOME/bin/java
CP=$CLASSPATH
CP=$CP:$UMAIL_HOME/lib/common/ceno-base.jar
CP=$CP:$UMAIL_HOME/lib/common/nmq.jar
CP=$CP:$UMAIL_HOME/lib/common/j2ee.jar


$JAVA_EXE -cp $CP naisa.ares.nmq.NmqUtil $CENO_HOME/queue/umail/mlist -mini_count=4  -mid_block_size=4096
$JAVA_EXE -cp $CP naisa.ares.nmq.NmqUtil $CENO_HOME/queue/umail/sync  -mini_count=4  -mid_block_size=4096
$JAVA_EXE -cp $CP naisa.ares.nmq.NmqUtil $CENO_HOME/queue/umail/event -mini_count=4  -mid_block_size=4096
chown -R ares:ares $CENO_HOME/queue/umail
