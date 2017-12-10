#!/usr/bin/python
#
# raspimirror.py
#
# MIT License
#
# Copyright (c) 2017 - Albert Casals, skarbat@gmail.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# This tool installs the MagicMirror software on top of a Raspbian image.
# It then becomes the RaspiMirror distro: http://raspimagic.mitako.eu
#
# It relies on the xsysroot tool: http://xsysroot.mitako.eu/
#
# Syntax: python raspimirror.py <xsysroot_profile> [ RENEW ]
#

import os
import sys
import time
import re

import xsysroot

def get_mm_modules(mm_file='mm_modules.txt'):
    '''
    Returns a list of URLs to Magic Mirror third party modules
    These are the github repositories ready to be cloned
    '''
    modules=[]
    try:
        with open(mm_file, 'r') as mfile:
            modules=mfile.read().splitlines()
    except:
        pass
            
    return modules


if __name__ == '__main__':

    # TODO: use command line options
    mm_version='1.0'
    pi_username='pi'
    hostname='raspimirror'

    print '>>> RaspiMirror builder {} starts on {}'.format(mm_version, time.ctime())

    if len(sys.argv) < 2:
        print 'syntax: magicmirror-build <xsysroot-profile> [RENEW]'
        sys.exit(1)
    else:
        xsysroot_profile=sys.argv[1]

    renew_image = len(sys.argv) > 2 and sys.argv[2] == 'RENEW'
    xmagic=xsysroot.XSysroot(xsysroot_profile)

    # Sanity check
    if xmagic.running():
        print 'Image is busy, please close processes and try again'
        sys.exit(1)

    # Either mount the current Raspbian image, or RENEW it to start from a clean copy.
    if not renew_image:
        print '>>> Mounting Raspbian image'
        xmagic.mount()
        if not xmagic.is_mounted():
            sys.exit(1)
    else:
        print '>>> Renewing Raspbian image'
        xmagic.umount()
        xmagic.renew()
        xmagic.umount()
        xmagic.expand()
        xmagic.mount()
        if not xmagic.is_mounted():
            sys.exit(1)

    # Automate APT to proceed unattended
    xmagic.edfile('/etc/apt/apt.conf.d/90forceyes', 'APT::Get::Assume-Yes "true";', append=False)

    # add pipaos software repository
    xmagic.edfile('/etc/apt/sources.list.d/mitako.list', 'deb http://archive.mitako.eu/ jessie main')
    xmagic.execute('curl -sL deb http://archive.mitako.eu/archive-mitako.gpg.key | apt-key add -', pipes=True)

    # Copy customization files for: Fixup partition names, and custom config.txt
    os.system('sudo cp -fv {} {}'.format('sysfiles/config.txt', xmagic.query('sysboot')))
    os.system('sudo cp -fv {} {}'.format('sysfiles/cmdline.txt', xmagic.query('sysboot')))
    os.system('sudo cp -fv {} {}/etc'.format('sysfiles/fstab', xmagic.query('sysroot')))
    os.system('sudo cp -fv {} {}/home/{}/.xinitrc'.format('sysfiles/xinitrc', xmagic.query('sysroot'), pi_username))

    # Copy customization files for: hide mouse, disable screen saver, disable wireless power safe mode
    xmagic.execute('mkdir -p .config/lxsession/LXDE-pi', as_user=pi_username)
    os.system('sudo cp -fv {} {}/home/{}/.config/lxsession/LXDE-pi'.format('sysfiles/autostart', xmagic.query('sysroot'), pi_username))

    xmagic.edfile('/etc/lightdm/lightdm.conf', '[SeatDefaults]', append=True)
    xmagic.edfile('/etc/lightdm/lightdm.conf', 'xserver-command=X -s 0 -dpms', append=True)

    xmagic.edfile('/etc/modprobe.d/8192cu.conf', '# Disable poewr saving')
    xmagic.edfile('/etc/modprobe.d/8192cu.conf', 'options 8192cu rtw_power_mgnt=0 rtw_enusbss=1 rtw_ips_mode=1', append=True)

    # Enable ssh service
    xmagic.execute('systemctl enable ssh')

    start_time=time.time()
    print '>>> MagicMirror installation starts at: {}'.format(time.ctime())

    # Execute the remote installation script, with automatic "no" response to using pm2
    print '>>> Starting MagicMirror official installation script'
    script_url='https://raw.githubusercontent.com/MichMich/MagicMirror/master/installers/raspberry.sh'
    install_command='echo "n" | bash <(curl -sL {})'.format(script_url)
    rc=xmagic.execute(install_command, as_user=pi_username, pipes=True)
    if rc:
        print '>>> MagicMirror installation FAILED rc={}'.format(rc)
        sys.exit(1)

    print '>>> Installing additional goodies'
    xmagic.execute('apt-get install -y unclutter')
    xmagic.edfile('/boot/raspimirror.txt', 'RaspiMagic v{} built on: {}'.format(mm_version, time.ctime(start_time)))
    xmagic.edfile('/boot/raspimirror.txt', 'Visit http://raspimirror.mitako.eu', append=True)

    # remove ssh password change warning popup
    xmagic.execute('apt-get purge -y pprompt')

    # Install PM2 manually, add a startup script
    print '>>> Installing PM2'
    xmagic.execute('npm config set unsafe-perm true', as_user=pi_username)
    xmagic.execute('cd ~/MagicMirror && sudo -E npm install -g pm2', as_user=pi_username, pipes=True)
    mm_file='/home/{}/mm.sh'.format(pi_username)
    os.system('sudo cp -fv {} {}/{}'.format('sysfiles/mm.sh', xmagic.query('sysroot'), mm_file))
    xmagic.execute('sudo chown {}:{} mm.sh'.format(pi_username, pi_username), as_user=pi_username)
    xmagic.execute('sudo chmod +x mm.sh', as_user=pi_username)

    # register PM2 to start at boot time
    xmagic.execute('pm2 startup systemd -u pi --hp /home/{}'.format(pi_username), as_user=pi_username)

    # Automatic wireless networking
    print '>>> Setting up automatic wireless networking'
    ifaces='/etc/network/interfaces'
    boot_supplicant='/boot/wpa_supplicant.txt'
    os.system('sudo cp -fv sysfiles/interfaces {}/{}'.format(xmagic.query('sysroot'), '/etc/network'))
    os.system('sudo cp -fv sysfiles/wpa_supplicant.txt {}'.format(xmagic.query('sysboot')))

    print '>>> Changing the hostname to: {}'.format(hostname)
    xmagic.edfile('/etc/hostname', hostname)
    xmagic.edfile('/etc/hosts', '127.0.1.1\t{}'.format(hostname), append=True)

    print '>>> Downloading Magic Mirror 3rd party modules'
    modules=get_mm_modules()
    for mm in modules:
        print '>>> Cloning {}'.format(mm)
        xmagic.execute('cd ~/MagicMirror/modules && git clone "{}"'.format(mm), pipes=True, as_user=pi_username)

    print '>>> RaspiMirror installation finished in {:5.3f} mins with rc={}'.format((time.time() - start_time) / 60, rc)
    sys.exit(rc)
