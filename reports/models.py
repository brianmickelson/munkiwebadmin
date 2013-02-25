from django.db import models
from datetime import datetime
import plistlib
from xml.parsers.expat import ExpatError
import base64
import bz2

class Machine(models.Model):
    mac = models.CharField(max_length=17, unique=True, primary_key=True)
    hostname = models.CharField(max_length=64)
    username = models.CharField(max_length=256)
    location = models.CharField(max_length=256)
    remote_ip = models.CharField(max_length=15)
    machine_model = models.CharField(max_length=64)
    cpu_type = models.CharField(max_length=64)
    cpu_speed = models.CharField(max_length=32)
    cpu_arch = models.CharField(max_length=32)
    ram = models.CharField(max_length=16)
    os_version = models.CharField(max_length=16)
    available_disk_space = models.IntegerField(default=0)
    serial_number = models.CharField(max_length=16)
    last_munki_update = models.DateTimeField(default=datetime(1, 1, 1, 0, 0))
    last_inventory_update = models.DateTimeField(
        default=datetime(1, 1, 1, 0, 0))
    class Meta:
        ordering = ['hostname']


class MunkiReport(models.Model):
    machine = models.ForeignKey(Machine)
    timestamp = models.DateTimeField(default=datetime.now())
    runtype = models.CharField(max_length=64)
    runstate = models.CharField(max_length=16)
    console_user = models.CharField(max_length=64)
    ard_info1 = models.CharField(max_length=64)
    ard_info2 = models.CharField(max_length=64)
    ard_info3 = models.CharField(max_length=64)
    ard_info4 = models.CharField(max_length=64)
    errors = models.IntegerField(default=0)
    warnings = models.IntegerField(default=0)
    activity = models.TextField(editable=False, null=True)
    report = models.TextField(editable=False, null=True)
    class Meta:
        ordering = ['machine']
        
    def hostname(self):
        return self.machine.hostname
        
    def mac(self):
        return self.machine.mac
    
    def encode(self, plist):
        string = plistlib.writePlistToString(plist)
        bz2data = bz2.compress(string)
        b64data = base64.b64encode(bz2data)
        return b64data
        
    def decode(self, data):
        # this has some sucky workarounds for odd handling
        # of UTF-8 data in sqlite3
        try:
            plist = plistlib.readPlistFromString(data)
            return plist
        except ExpatError:
            try:
                plist = plistlib.readPlistFromString(data.encode('UTF-8'))
                return plist
            except ExpatError:
                return self.b64bz_decode(data)
        
    def b64bz_decode(self, data):
        try:
            bz2data = base64.b64decode(data)
            string = bz2.decompress(bz2data)
            plist = plistlib.readPlistFromString(string)
            return plist
        except Exception:
            return {}
        
    def get_report(self):
        return self.decode(self.report)
        
    def get_activity(self):
        return self.decode(self.activity)
        
    def update_report(self, base64bz2report):
        # Save report.
        try:
            base64bz2report = base64bz2report.replace(" ", "+")
            plist = self.b64bz_decode(base64bz2report)
            #self.report = base64bz2report
            self.report = plistlib.writePlistToString(plist)
        except:
            plist = None
            self.report = ''

        if plist is None:
            self.activity = None
            self.errors = 0
            self.warnings = 0
            self.console_user = "<None>"
            self.ard_info1 = "<None>"
            self.ard_info2 = "<None>"
            self.ard_info3 = "<None>"
            self.ard_info4 = "<None>"
            return
        
        # Check activity.
        activity = dict()
        for section in ("ItemsToInstall",
                        "InstallResults",
                        "ItemsToRemove",
                        "RemovalResults",
                        "AppleUpdates"):
            if (section in plist) and len(plist[section]):
                activity[section] = plist[section]
        if activity:
            #self.activity = self.encode(activity)
            self.activity = plistlib.writePlistToString(activity)
        else:
            self.activity = None
        
        # Check errors and warnings.
        if "Errors" in plist:
            self.errors = len(plist["Errors"])
        else:
            self.errors = 0
        
        if "Warnings" in plist:
            self.warnings = len(plist["Warnings"])
        else:
            self.warnings = 0
        
        # Check console user.
        self.console_user = "unknown"
        if "ConsoleUser" in plist:
            self.console_user = unicode(plist["ConsoleUser"])
        
        # Check ARD Info.
        self.ard_info1 = "unknown"
        if "ARDInfo1" in plist:
            self.ard_info1 = unicode(plist["ARDInfo1"])
        self.ard_info2 = "unknown"
        if "ARDInfo2" in plist:
            self.ard_info2 = unicode(plist["ARDInfo2"])
        self.ard_info3 = "unknown"
        if "ARDInfo3" in plist:
            self.ard_info3 = unicode(plist["ARDInfo3"])
        self.ard_info4 = "unknown"
        if "ARDInfo4" in plist:
            self.ard_info4 = unicode(plist["ARDInfo4"])
