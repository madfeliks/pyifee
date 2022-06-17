from typing import Union, List
from enum import Enum
from logging import getLogger
from dbus import SystemBus, Interface, DBusException


SERVICE_SUCCESS = "service {0} {1} successfully"
SERVICE_FAILED  = "{0} service {1} failed: {2}"


MM_DBUS_PATH = '/org/freedesktop/ModemManager1'
MM_DBUS_PROXY = 'org.freedesktop.ModemManager1'
MM_DBUS_SERVICE = 'org.freedesktop.ModemManager1'
MM_DBUS_INTERFACE = 'org.freedesktop.DBus.ObjectManager'
MM_DBUS_INTERFACE_MODEM = 'org.freedesktop.ModemManager1.Modem'
MM_DBUS_INTERFACE_SIGNAL = 'org.freedesktop.ModemManager1.Modem.Signal'
DBUS_INTERFACE_PROPERTIES = 'org.freedesktop.DBus.Properties'
SYSTEMD_DBUS_PATH = '/org/freedesktop/systemd1'
SYSTEMD_DBUS_PROXY = 'org.freedesktop.systemd1'
SYSTEMD_DBUS_SERVICE = 'org.freedesktop.systemd1'
SYSTEMD_DBUS_INTERFACE  = 'org.freedesktop.systemd1.Manager'
SYSTEMD_DBUS_INTERFACE_UNIT = 'org.freedesktop.systemd1.Unit'
NM_DBUS_PATH =  '/org/freedesktop/NetworkManager'
NM_DBUS_PATH_SETTINGS = '/org/freedesktop/NetworkManager/Settings'
NM_DBUS_PROXY = 'org.freedesktop.NetworkManager'
NM_DBUS_SERVICE = 'org.freedesktop.NetworkManager'
NM_DBUS_SERVICE_SETTINGS = 'org.freedesktop.NetworkManager.Settings'
NM_DBUS_SERVICE_CONNECTION = 'org.freedesktop.NetworkManager.Settings.Connection'
NM_DBUS_CONNECTION_ACTIVE  = 'org.freedesktop.NetworkManager.Connection.Active'


class CModemTechs(Enum):
    UNKNOWN = 0
    POTS = 1
    GSM = 2
    GSM_COMPACT = 4
    GPRS = 8
    EDGE = 16
    UMTS = 32
    HSDPA = 64
    HSUPA = 128
    HSPA = 256
    HSPA_PLUS = 512
    RTT1X = 1024
    EVDO0 = 2048
    EVDOA = 4096
    EVDOB = 8192
    LTE = 16384
    NR5G = 32768
    ANY = 4294967295


class CModemStates(Enum):
    FAILED = -1
    UNKNOWN = 0
    INITIALIZING = 1
    LOCKED = 2
    DISABLED = 3
    DISABLING = 4
    ENABLING = 5
    ENABLED = 6
    SEARCHING = 7
    REGISTERED = 8
    DISCONNECTING = 9
    CONNECTING = 10
    CONNECTED = 11


class CModemFailedReason(Enum):
    NONE = 0
    UNKNOWN = 1
    SIM_MISSING = 2
    SIM_ERROR = 3


class CModemPowerStates(Enum):
    UNKNOWN = 0
    OFF = 1
    LOW = 2
    ON  = 3


def find_access_tech(p_value: int) -> List[str]:
    if p_value == CModemTechs.UNKNOWN.value:
        return [CModemTechs.UNKNOWN.name]
    if p_value == CModemTechs.ANY.value:
        return [CModemTechs.ANY.name]
    ret = []
    for i in range(32,0,-1):
        if p_value >= (2**i):
            ret.append(CModemTechs(2**i).name)
            p_value =- (2**i)
    return ret


class CSystemdService():
    def __init__(self, p_service: str) -> None:
        self.__name = p_service + '.service'
        self.__log  = getLogger('[systemd]')

        bus = SystemBus()

        self.__systemd = bus.get_object(SYSTEMD_DBUS_PROXY, SYSTEMD_DBUS_PATH)
        self.__manager = Interface(self.__systemd, SYSTEMD_DBUS_INTERFACE)

        try:
            self.__service = bus.get_object(SYSTEMD_DBUS_SERVICE, object_path=self.__manager.LoadUnit(self.__name))
            self.__interface = Interface(self.__service, dbus_interface=DBUS_INTERFACE_PROPERTIES)
        except DBusException as err:
            raise RuntimeError(f"[{self.__name}] {str(err)}") from err

    def __str__(self) -> str:
        return str({'name': self.__name, 'status': self.state})

    def state(self) -> str:
        return str(self.__interface.Get(SYSTEMD_DBUS_INTERFACE_UNIT, 'SubState'))

    def enabled(self) -> bool:
        return bool(str(self.__interface.Get(SYSTEMD_DBUS_INTERFACE_UNIT, 'UnitFileState')) == 'enabled')

    def stop(self) -> None:
        if self.state() == 'running':
            try:
                self.__manager.StopUnit(self.__name, 'replace')
                msg = SERVICE_SUCCESS.format(self.__name, 'stopped')
                self.__log.debug(msg)
            except DBusException as err:
                msg = SERVICE_FAILED.format(self.__name, 'stopping', str(err))
                self.__log.error(msg)

    def start(self) -> None:
        if self.state() != 'running':
            try:
                self.__manager.StartUnit(self.__name, 'replace')
                msg = SERVICE_SUCCESS.format(self.__name, 'started')
                self.__log.debug(msg)
            except DBusException as err:
                msg = SERVICE_FAILED.format('starting', self.__name, str(err))
                self.__log.error(msg)

    def enable(self) -> None:
        if not self.enabled():
            try:
                self.__manager.EnableUnitFiles([self.__name], False, True)
                self.__manager.Reload()
                msg = SERVICE_SUCCESS.format(self.__name, 'enabled')
                self.__log.debug(msg)
            except DBusException as err:
                msg = SERVICE_FAILED.format('enabling', self.__name, str(err))
                self.__log.error(msg)

    def disable(self) -> None:
        if self.enabled():
            try:
                self.__manager.DisableUnitFiles([self.__name], False)
                self.__manager.Reload()
                msg = SERVICE_SUCCESS.format(self.__name, 'disabled')
                self.__log.debug(msg)
            except DBusException as err:
                msg = SERVICE_FAILED.format('disabling', self.__name, str(err))
                self.__log.error(msg)


class CConnection():
    def __init__(self, p_conn: dict) -> None:
        try:
            self.__id   = p_conn['id']
            self.__path = p_conn['path']
        except KeyError as err:
            raise RuntimeError(f"[connection] init: incorrect format {str(err)}") from err

        self.__path_active = None
        self.__bus = SystemBus()

        try:
            proxy = self.__bus.get_object(NM_DBUS_SERVICE, self.__path)
            self.__iface = Interface(proxy, NM_DBUS_SERVICE_CONNECTION)
            nm_proxy = self.__bus.get_object(NM_DBUS_PROXY, NM_DBUS_PATH)
            self.__nm_iface = Interface(nm_proxy, NM_DBUS_SERVICE)
        except DBusException as err:
            raise RuntimeError(f"[{self.__id}] init: {str(err)}") from err

        self.__log = getLogger(f"[{self.__id}]")

    def __str__(self) -> str:
        return str(self.__id)

    @property
    def autoconnect(self) -> bool:
        settings = self.__iface.GetSettings()
        try:
            autoconnect = settings['connection']['autoconnect']
        except KeyError:
            return True

        return bool(autoconnect)

    @autoconnect.setter
    def autoconnect(self, p_val: bool) -> None:
        try:
            assert isinstance(p_val, bool)
            settings = self.__iface.GetSettings()
            settings['connection']['autoconnect'] = p_val
            self.__iface.Update(settings)
            msg = f"autoconnect - {p_val}"
            self.__log.debug(msg)
        except (AssertionError, DBusException) as err:
            raise RuntimeError(f"[{self.__id}] could not set autoconnect to {p_val}") from err

    @property
    def connect(self) -> bool:
        try:
            proxy = self.__bus.get_object(NM_DBUS_PROXY, NM_DBUS_PATH)
            props = Interface(proxy, DBUS_INTERFACE_PROPERTIES)
        except DBusException as err:
            raise RuntimeError(f"[{self.__id}] {str(err)}") from err

        for a_conn in list(props.Get(NM_DBUS_SERVICE, 'ActiveConnections')):
            a_proxy = self.__bus.get_object(NM_DBUS_PROXY, a_conn)
            a_props = Interface(a_proxy, DBUS_INTERFACE_PROPERTIES)
            conn  = a_props.Get(NM_DBUS_CONNECTION_ACTIVE, 'Connection')
            conn_proxy = self.__bus.get_object(NM_DBUS_PROXY, conn)
            conn_iface = Interface(conn_proxy, NM_DBUS_SERVICE_CONNECTION)
            settings = conn_iface.GetSettings()
            if settings['connection']['id'] == self.__id:
                self.__path_active = a_conn
                return True

        self.__path_active = None
        return False

    @connect.setter
    def connect(self, p_val: bool) -> None:
        try:
            assert isinstance(p_val, bool)
            match (self.connect, p_val):
                case (True, True):
                    msg = "already activated"
                case (False, True):
                    self.__nm_iface.ActivateConnection(self.__path, '/', '/')
                    msg = "activate successfully"
                case (False, False):
                    msg = "already deactivated"
                case (True, False):
                    self.__nm_iface.DeactivateConnection(self.__path_active)
                    msg = "activate successfully"
            self.__log.debug(msg)
        except (AssertionError, DBusException) as err:
            raise RuntimeError(f"[{self.__id}] {str(err)}") from err


class CNetworkManager():
    def __init__(self) -> None:
        self.__bus = SystemBus()

    def get(self, p_id: str) -> Union[CConnection, None]:
        try:
            proxy = self.__bus.get_object(NM_DBUS_PROXY, NM_DBUS_PATH_SETTINGS)
            iface = Interface(proxy, NM_DBUS_SERVICE_SETTINGS)
        except DBusException as err:
            raise RuntimeError(f"[network manager] {str(err)}") from err

        for conn in iface.ListConnections():
            conn_proxy = self.__bus.get_object(NM_DBUS_SERVICE, conn)
            conn_iface = Interface(conn_proxy, NM_DBUS_SERVICE_CONNECTION)
            settings = conn_iface.GetSettings()
            if str(settings['connection']['id']) == p_id:
                return CConnection({'id': p_id, 'path': str(conn)})

        return None


class CModem():
    def __init__(self, p_path: str) -> None:
        self.__conn = None
        self.__path = p_path
        self.__bus = SystemBus()
        self.__proxy = self.__bus.get_object(MM_DBUS_PROXY, self.__path)
        self.__iface = Interface(self.__proxy, dbus_interface=DBUS_INTERFACE_PROPERTIES)
        self.__log = getLogger(f"[modem {p_path.split('/')[-1]}]")

    @property
    def connection(self) -> Union[str, None]:
        return self.__conn

    @connection.setter
    def connection(self, p_name: str) -> None:
        self.__conn = p_name

    @property
    def index(self) -> int:
        return int(self.__path.split('/')[-1])

    @property
    def properties(self) -> dict:
        property_dict = {}
        try:
            property_dict['Sim'] = str(self.__iface.Get(\
                    MM_DBUS_INTERFACE_MODEM, \
                    'Sim'\
                    ))
            property_dict['Manufacturer'] = str(self.__iface.Get(\
                    MM_DBUS_INTERFACE_MODEM, \
                    'Manufacturer'\
                    ))
            property_dict['Model'] = str(self.__iface.Get(\
                    MM_DBUS_INTERFACE_MODEM, \
                    'Model'\
                    ))
            property_dict['Revision'] = str(self.__iface.Get(\
                    MM_DBUS_INTERFACE_MODEM, \
                    'Revision'\
                    ))
            property_dict['Device'] = str(self.__iface.Get(\
                    MM_DBUS_INTERFACE_MODEM, \
                    'Device'\
                    ))
            property_dict['PrimaryPort'] = str(self.__iface.Get(\
                    MM_DBUS_INTERFACE_MODEM, \
                    'PrimaryPort'\
                    ))
            property_dict['Ports'] = ','.join([str(p[0]) for p in self.__iface.Get(\
                    MM_DBUS_INTERFACE_MODEM, \
                    'Ports'\
                    )])
            property_dict['IMEI'] = str(self.__iface.Get(\
                    MM_DBUS_INTERFACE_MODEM, \
                    'EquipmentIdentifier'\
                    ))
            property_dict['State'] = CModemStates(int(self.__iface.Get(\
                    MM_DBUS_INTERFACE_MODEM, \
                    'State'\
                    ))).name
            property_dict['FailedReason'] = CModemFailedReason(int(self.__iface.Get(\
                    MM_DBUS_INTERFACE_MODEM, \
                    'StateFailedReason'\
                    ))).name
            property_dict['SignalQuality'] = int(self.__iface.Get(\
                    MM_DBUS_INTERFACE_MODEM, \
                    'SignalQuality'\
                    )[0])
            property_dict['PowerState'] = CModemPowerStates(int(self.__iface.Get(\
                    MM_DBUS_INTERFACE_MODEM, \
                    'PowerState'\
                    ))).name
            property_dict['AccessTechnologies'] = ','.join(find_access_tech(\
                    int(self.__iface.Get(\
                            MM_DBUS_INTERFACE_MODEM, \
                            'AccessTechnologies'\
                            ))\
                    ))
        except(DBusException, IndexError) as err:
            msg = f"error ocured when tring to get properties: {str(err)}"
            self.__log.error(msg)

        return property_dict

    @property
    def signal(self) -> dict:
        try:
            prop_iface = Interface(self.__proxy, dbus_interface=DBUS_INTERFACE_PROPERTIES)
            signal_iface = Interface(self.__proxy, dbus_interface=MM_DBUS_INTERFACE_SIGNAL)
            signal_iface.Setup(1)

            for mode in ['Gsm', 'Umts', 'Lte', 'Cdma', 'Evdo']:
                signal_raw = dict(prop_iface.Get(MM_DBUS_INTERFACE_SIGNAL, mode)).items()
                signal_ret = {}
                if len(signal_raw):
                    for item in signal_raw:
                        signal_ret[str(item[0])] = float(item[1])
                    return signal_ret
        except(DBusException, IndexError) as err:
            msg = f"error ocured when tring to get modem signal: {str(err)}"
            self.__log.error(msg)

        return {}

    def reset(self) -> None:
        iface = Interface(self.__proxy, dbus_interface=MM_DBUS_INTERFACE_MODEM)

        try:
            iface.Reset()
        except DBusException as err:
            msg = f"reset failed: {str(err)}"
            self.__log.error(msg)

    def enable(self) -> bool:
        iface = Interface(self.__proxy, dbus_interface=MM_DBUS_INTERFACE_MODEM)

        network_manager = CNetworkManager()
        conn = network_manager.get(self.__conn)

        properties = self.properties

        if len(properties) == 0:
            return False

        match properties['PowerState']:
            case CModemPowerStates.ON.name:
                pass
            case _:
                try:
                    iface.SetPowerState(CModemPowerStates.ON.value)
                    msg = "powered on successfully"
                    self.__log.info(msg)
                except DBusException as err:
                    msg = f"powered on failed: {str(err)}"
                    self.__log.error(msg)
                    return False

        match properties['State']:
            case CModemStates.FAILED.name:
                msg = f"enabling connection {self.__conn} failed: {properties['FailedReason']}"
                self.__log.error(msg)
                return False
            case CModemStates.ENABLING.name|CModemStates.ENABLED.name|CModemStates.CONNECTING.name|CModemStates.CONNECTED.name|CModemStates.REGISTERED.name:
                return True
            case _:
                try:
                    iface.Enable(True)
                    msg = f"connection {self.__conn} enabled successfully"
                    self.__log.info(msg)
                    conn.autoconnect = True
                    msg = f"autoconnect on for {self.__conn}"
                    self.__log.info(msg)
                    return True
                except DBusException as err:
                    msg = f"enabling connection {self.__conn} failed: {str(err)}"
                    self.__log.error(msg)
                    return False

    def disable(self) -> bool:
        iface = Interface(self.__proxy, dbus_interface=MM_DBUS_INTERFACE_MODEM)
        network_manager = CNetworkManager()
        conn = network_manager.get(self.__conn)

        properties = self.properties

        if len(properties) == 0:
            return False

        match properties['State']:
            case CModemStates.FAILED.name:
                msg = f"disabling connection {self.__conn} failed: {properties['FailedReason']}"
                self.__log.error(msg)
                return False
            case CModemStates.DISABLING.name|CModemStates.DISABLED.name:
                pass
            case _:
                try:
                    conn.autoconnect = False
                    msg = f"autoconnect off for {self.__conn}"
                    self.__log.info(msg)
                    iface.Enable(False)
                    msg = f"connection {self.__conn} disabled successfuly"
                    self.__log.info(msg)
                except DBusException as err:
                    msg = f"disabling connection {self.__conn} failed: {str(err)}"
                    self.__log.error(msg)
                    return False

        match properties['PowerState']:
            case CModemPowerStates.LOW.name:
                return True
            case _:
                try:
                    iface.SetPowerState(CModemPowerStates.LOW.value)
                    msg = "powered off successfully"
                    self.__log.info(msg)
                    return True
                except DBusException as err:
                    msg = f"powered off failed: {str(err)}"
                    self.__log.error(msg)
                    return False


class CModemManager():
    def __init__(self) -> None:
        self.__bus = SystemBus()

        try:
            proxy = self.__bus.get_object(MM_DBUS_PROXY, MM_DBUS_PATH)
            self.__iface = Interface(proxy, MM_DBUS_INTERFACE)
        except DBusException as err:
            raise RuntimeError(f"[modem manager] init error: {str(err)}") from err

    @property
    def modems(self) -> List:
        try:
            return [CModem(str(modem)) for modem in list(self.__iface.GetManagedObjects())]
        except DBusException as err:
            raise RuntimeError(f"[modem manager] get modems: {str(err)}") from err
