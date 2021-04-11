import pexpect

from climatic.CoreCli import CoreCli
from climatic.connections.Ssh import Ssh
from climatic.connections.Ssh import PTY_WINSIZE_COLS as SSH_PTY_WINSIZE_COLS
from climatic.connections.Ser2Net import Ser2Net
from climatic.connections.Ser2Net import PTY_WINSIZE_COLS as SER2NET_PTY_WINSIZE_COLS
from typing import Optional


####################################################################################################
## OcNOS

class OcNOS(CoreCli):
    """ Extend CoreCli with IP Infusion's OcNOS customizations.
    """

    def __init__(self, connection, **opts):
        """ Initialize OcNOS CLI.
        @param connection  The connection object to be used for accessing the CLI.
        @param opts        Same options as CoreCli initializer.
        """
        if not 'marker' in opts:
            self.marker = '\n[^ ]+#'
        if not 'error_marker' in opts:
            self.error_marker = '%'

        CoreCli.__init__(self,
                         connection,
                         **opts)

####################################################################################################
## SshOcNOS

class SshOcNOS(OcNOS):
    """ Connects to a OcNOS CLI using SSH.
    """

    def __init__(self,
                 ip: str,
                 username: Optional[str]="ocnos",
                 password: Optional[str]="ocnos",
                 port: Optional[int]=22,
                 **opts):
        """ Initialize SSH OcNOS CLI.
        @param ip          IP address of target. Ex: '234.168.10.12'
        @param username    username for opening SSH connection
        @param password    password for authentication in SSH connection
        @param port        Port used for SSH connection. Defaults to 22
        @param opts        Same options as CoreCli initializer.
        """
        self.name = "OcNOS.SSH"
        ssh = Ssh(ip, username, port=port)
        OcNOS.__init__(self,
                       ssh,
                       username=username,
                       password=password,
                       pty_winsize_cols=SSH_PTY_WINSIZE_COLS,
                       **opts)

    def login(self):
        """ Login to CLI interface.
        """
        while True:
            index = self.connection.terminal.expect(
                ['Are you sure you want to continue connecting',
                 'password',
                 r'\n[^\s]+>',
                 r'\n[^\s]+#'],
                timeout=10)

            if index == 0:
                self.connection.terminal.sendline('yes')
            if index == 1:
                self.connection.terminal.waitnoecho()
                self.connection.terminal.sendline(self.password)
            if index == 2:
                self.connection.terminal.sendline('enable')
            if index >= 3:
                break

    def logout(self):
        """ Logout from CLI interface.
        """
        # Send exit until login is reached.
        self.connection.terminal.sendline()
        self.connection.terminal.expect(r'\n[^ ]+#', timeout=5)
        self.connection.terminal.sendline('exit')
        self.connection.terminal.expect(r'\n[^ ]+>', timeout=5)
        self.connection.terminal.sendline('exit')


####################################################################################################
## Ser2NetOcNOS

class Ser2NetOcNOS(OcNOS):
    """ Connects to a OcNOS CLI using Ser2Net.
    """

    def __init__(self,
                 ip: str,
                 port: int,
                 username: Optional[str]="ocnos",
                 password: Optional[str]="ocnos",
                 **opts):
        """ Initialize OcNOS CLI.
        @param ip        IP address of target. Ex: '234.168.10.12'
        @param port      The port corresponding to the desired serial device.
        @param username  username for authentication to OcNOS.
        @param password  password for authentication to OcNOS.
        @param opts        Same options as CoreCli initializer.
        """
        self.name = "OcNOS.Ser2Net"
        ser2net = Ser2Net(ip, port)
        OcNOS.__init__(self,
                       ser2net,
                       username=username,
                       password=password,
                       pty_winsize_cols=SER2NET_PTY_WINSIZE_COLS,
                       **opts)

    def login(self):
        """ Login to CLI interface.
        """
        iteration = 0
        while True:
            index = self.connection.terminal.expect(
                ['login', 'Password', r'\n[^\s]*>', r'\n[^\s]*#', pexpect.TIMEOUT],
                timeout=self.timeout)

            if index == 0:
                break
            else:
                iteration = iteration + 1
                if iteration >= 10:
                    TimeoutError("Could not reach login prompt after 10 iterations. Aborting!")
                self.connection.terminal.sendcontrol('d')

        # Enter credentials
        self.connection.terminal.sendline(self.username)
        self.connection.terminal.expect('Password:')
        self.connection.terminal.waitnoecho()
        self.connection.terminal.sendline(self.password)
        self.connection.terminal.expect(r'\n[^ ]+>', timeout=self.timeout)
        self.connection.terminal.sendline('enable')
        self.connection.terminal.expect(r'\n[^ ]+#', timeout=self.timeout)


    def logout(self):
        """ Logout from CLI interface.
        """
        # To avoid deadlock in the while loop, just send a new line when there is an active
        # match. This means it was not terminated by an exception
        if self.connection.terminal.match != None:
            self.connection.terminal.sendline()

        while True:
            index = self.connection.terminal.expect(['login:', 'closed', r'\n[^\s]*>', r'\n[^\s]*#'],
                                                    timeout=self.timeout)
            if index <= 1:
                break
            else:
                self.connection.terminal.sendcontrol('d')
