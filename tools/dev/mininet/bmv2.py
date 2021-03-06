from mininet.log import error, info
from mininet.node import Switch
from os import environ
from os.path import isfile


class ONOSBmv2Switch(Switch):
    """BMv2 software switch """

    thriftPort = 9090
    deviceId = 0

    def __init__(self, name, thriftPort=None, deviceId=None, debugger=False,
                 loglevel="warn", elogger=False, persistent=True, **kwargs):
        Switch.__init__(self, name, **kwargs)
        self.swPath = environ['BMV2_EXE']
        self.jsonPath = environ['BMV2_JSON']
        if not thriftPort:
            self.thriftPort = ONOSBmv2Switch.thriftPort
            ONOSBmv2Switch.thriftPort += 1
        else:
            self.thriftPort = thriftPort
            ONOSBmv2Switch.thriftPort = max(thriftPort, ONOSBmv2Switch.thriftPort)
        if not deviceId:
            if self.dpid:
                self.deviceId = int(self.dpid, 0 if 'x' in self.dpid else 16)
            else:
                self.deviceId = ONOSBmv2Switch.deviceId
                ONOSBmv2Switch.deviceId += 1
        else:
            self.deviceId = deviceId
            ONOSBmv2Switch.deviceId = max(deviceId, ONOSBmv2Switch.deviceId)
        self.debugger = debugger
        self.loglevel = loglevel
        self.logfile = '/tmp/bmv2-%d.log' % self.deviceId
        self.output = open(self.logfile, 'w')
        self.elogger = elogger
        self.persistent = persistent
        if persistent:
            self.exectoken = "/tmp/bmv2-%d-exec-token" % self.deviceId
            self.cmd("touch %s" % self.exectoken)

    @classmethod
    def setup(cls):
        err = False

        if 'BMV2_EXE' not in environ:
            error("ERROR! environment var $BMV2_EXE not set\n")
            err = True
        elif not isfile(environ['BMV2_EXE']):
            error("ERROR! BMV2_EXE=%s: no such file\n" % environ['BMV2_EXE'])
            err = True

        if 'BMV2_JSON' not in environ:
            error("ERROR! environment var $BMV2_JSON not set\n")
            err = True
        elif not isfile(environ['BMV2_JSON']):
            error("ERROR! BMV2_JSON=%s: no such file\n" % environ['BMV2_JSON'])
            err = True

        if err:
            exit(1)

    def start(self, controllers):
        args = [self.swPath, '--device-id %s' % str(self.deviceId)]
        for port, intf in self.intfs.items():
            if not intf.IP():
                args.append('-i %d@%s' % (port, intf.name))
        if self.thriftPort:
            args.append('--thrift-port %d' % self.thriftPort)
        if self.elogger:
            nanomsg = 'ipc:///tmp/bmv2-%d-log.ipc' % self.deviceId
            args.append('--nanolog %s' % nanomsg)
        if self.debugger:
            args.append('--debugger')
        args.append('--log-console -L%s' % self.loglevel)
        args.append(self.jsonPath)

        assert controllers[0]
        c = controllers[0]
        args.append('--')
        args.append('--controller-ip %s' % c.IP())
        args.append('--controller-port %d' % c.port)

        bmv2cmd = " ".join(args)

        info("\nStarting BMv2 target: %s\n" % bmv2cmd)

        if self.persistent:
            # Re-exec the switch if it crashes.
            cmdStr = "(while [ -e {} ]; " \
                     "do {} ; " \
                     "sleep 1; " \
                     "done;) > {} 2>&1 &".format(self.exectoken, bmv2cmd, self.logfile)
        else:
            cmdStr = "{} > {} 2>&1 &".format(bmv2cmd, self.logfile)

        self.cmd(cmdStr)

    def stop(self):
        "Terminate switch."
        self.output.flush()
        if self.persistent:
            self.cmd("rm -f %s" % self.exectoken)
        self.cmd('kill %' + self.swPath)
        self.deleteIntfs()


### Exports for bin/mn

switches = {'onosbmv2': ONOSBmv2Switch}
