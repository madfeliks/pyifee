from os import makedirs as m_mkdir, path as m_path
from typing import Union, List
from datetime import datetime as m_dt
from dataclasses import dataclass, field
from queue import Queue
import json


COULD_NOT_SET = "[{module}] could not set {unit} {aux}"
COULD_NOT_GET = "[{module}] could not get {unit} {aux}"


class CCacheICAO():
    def __init__(self, p_path: str) -> None:
        self.__path = p_path
        self.__time = 0
        self.__icao = None

        try:
            if m_path.isfile(self.__path):
                with open(self.__path, 'r', encoding='UTF8') as cache:
                    data = json.loads(cache.read())
                    self.__icao = data['icao']
                    self.__time = int(data['time'])
        except(json.decoder.JSONDecodeError, KeyError) as err:
            raise RuntimeError(COULD_NOT_GET.format(module='icao', unit='icao', aux='from cache')) from err

    def __str__(self) -> str:
        return ','.join([f"path:{self.__path}", f"time:{self.__time}", f"icao:{self.__icao}"])

    def as_dict(self) -> dict:
        return {'path': self.__path, 'time': self.__time, 'icao': self.__icao}

    def __getattr__(self, p_key: str) -> Union[int, str, None]:
        match p_key:
            case "path":
                return self.__path
            case "time":
                return self.__time
            case "icao":
                return self.__icao
            case _:
                return None

    def save(self, p_icao: str) -> None:
        self.__time = int(m_dt.now().timestamp())
        self.__icao = p_icao
        try:
            m_mkdir(m_path.dirname(self.__path), mode=493, exist_ok=True)
            with open(self.__path, 'w', encoding='UTF8') as cache:
                cache.write(json.dumps({'time': self.__time, 'icao': self.__icao}))
        except OSError as err:
            raise RuntimeError(COULD_NOT_SET.format(module='icao', unit='icao', aux='to cache')) from err


@dataclass
class CBattery():
    __index: int
    __power: int
    __level: int

    @property
    def power(self) -> Union[int, float]:
        return round(self.__power, 2)

    @power.setter
    def power(self, p_val: Union[int, float]) -> None:
        try:
            assert isinstance(p_val, Union[int, float])
            self.__power = p_val
        except AssertionError as err:
            raise RuntimeError(COULD_NOT_SET.format(module='battery', unit='power')) from err

    @property
    def level(self) -> int:
        return self.__level

    @level.setter
    def level(self, p_val: int) -> None:
        try:
            assert isinstance(p_val, int)
            self.__level = p_val
        except AssertionError as err:
            raise RuntimeError(COULD_NOT_SET.format(module='battery', unit='level')) from err

    def __str__(self) -> str:
        return ','.join([f"name:{self.__index}", f"power:{self.__power}", f"level:{self.__level}"])

    def as_dict(self) -> dict:
        return {'index': self.__index, 'power': self.__power, 'level': self.__level}


@dataclass
class CTemperature():
    __name:  str
    __value: Union[float, int]

    @property
    def value(self) -> Union[float, int]:
        return round(self.__value, 2)

    @value.setter
    def value(self, p_val: Union[float, int]) -> None:
        try:
            assert isinstance(p_val, (float, int))
            self.__value = float(p_val)
        except AssertionError as err:
            raise RuntimeError(COULD_NOT_SET.format(module='temperature', unit='value')) from err

    def __str__(self) -> str:
        return ','.join([f"name:{self.__name}", f"value:{self.__value}"])

    def as_dict(self) -> dict:
        return {'name': self.__name, 'value': self.__value}


@dataclass
class CPosition():
    __lat: Union[float, None] = None
    __lon: Union[float, None] = None

    @property
    def lat(self) -> Union[float, None]:
        return self.__lat

    @lat.setter
    def lat(self, p_val: float) -> None:
        try:
            assert isinstance(p_val, float)
            self.__lat = p_val
        except AssertionError as err:
            raise RuntimeError(COULD_NOT_SET.format(module='latitude', unit='value')) from err

    @property
    def lon(self) -> Union[float, None]:
        return self.__lon

    @lon.setter
    def lon(self, p_val: float) -> None:
        try:
            assert isinstance(p_val, float)
            self.__lon = p_val
        except AssertionError as err:
            raise RuntimeError(COULD_NOT_SET.format(module='longitude', unit='value')) from err

    def __str__(self) -> str:
        return ','.join([f"lat:{self.__lat}", f"lon:{self.__lon}"])

    def as_dict(self) -> dict:
        return {'lat': self.__lat, 'lon': self.__lon}


@dataclass
class CSyncMonitoring():
    __pwr: bool               = True
    __bat: List[CBattery]     = field(default_factory=list)
    __tmp: List[CTemperature] = field(default_factory=list)
    __pos: CPosition          = CPosition()
    __vel: int                = 0
    __alt: int                = 0

    @property
    def pwr(self) -> bool:
        return self.__pwr

    @pwr.setter
    def pwr(self, p_val: bool) -> None:
        try:
            assert isinstance(p_val, bool)
            self.__pwr = p_val
        except AssertionError as err:
            raise RuntimeError(COULD_NOT_SET.format(module='power unit', unit='state')) from err

    @property
    def bat(self) -> List[CBattery]:
        return self.__bat

    @bat.setter
    def bat(self, p_val: List[CBattery]) -> None:
        try:
            assert isinstance(p_val, list)
            self.__bat = p_val
        except AssertionError as err:
            raise RuntimeError(COULD_NOT_SET.format(module='batteries', unit='states')) from err

    @property
    def tmp(self) -> List[CTemperature]:
        return self.__tmp

    @tmp.setter
    def tmp(self, p_val: List[CTemperature]) -> None:
        try:
            assert isinstance(p_val, list)
            self.__tmp = p_val
        except AssertionError as err:
            raise RuntimeError(COULD_NOT_SET.format(module='temperatures', unit='values')) from err

    @property
    def vel(self) -> int:
        return self.__vel

    @vel.setter
    def vel(self, p_val: int) -> None:
        try:
            assert isinstance(p_val, int)
            self.__vel = p_val
        except AssertionError as err:
            raise RuntimeError(COULD_NOT_SET.format(module='velocity', unit='speed')) from err

    @property
    def alt(self) -> int:
        return self.__alt

    @alt.setter
    def alt(self, p_val: int) -> None:
        try:
            assert isinstance(p_val, int)
            self.__alt = p_val
        except AssertionError as err:
            raise RuntimeError(COULD_NOT_SET.format(module='altitude', unit='value')) from err

    @property
    def pos(self) -> CPosition:
        return self.__pos

    @pos.setter
    def pos(self, p_val: CPosition) -> None:
        try:
            assert isinstance(p_val, CPosition)
            self.__pos = p_val
        except AssertionError as err:
            raise RuntimeError(COULD_NOT_SET.format(module='position', unit='lotitude, longitude')) from err

    def as_dict(self) -> dict:
        ret = {}
        ret['powerunit'] = int(self.__pwr)
        ret['batteries'] = [bat.as_dict() for bat in self.__bat]
        ret['temperature'] = [tmp.as_dict() for tmp in self.__tmp]
        ret['velocity'] = self.__vel
        ret['altitude'] = self.__alt
        ret['position'] = self.__pos.as_dict()
        return ret

    def __str__(self) -> str:
        return str(self.as_dict())


@dataclass
class CSyncADSB():
    __icao:   Union[str, None] = None
    __active: bool             = True
    msg:      Queue            = Queue()

    @property
    def icao(self) -> Union[str, None]:
        return self.__icao

    @icao.setter
    def icao(self, p_val: Union[str, None]) -> None:
        try:
            assert isinstance(p_val, Union[str, None])
            self.__icao = p_val
        except AssertionError as err:
            raise RuntimeError(COULD_NOT_SET.format(module='adsb', unit='value')) from err

    @property
    def active(self) -> bool:
        return self.__active

    @active.setter
    def active(self, p_val: bool) -> None:
        try:
            assert isinstance(p_val, bool)
            self.__active = p_val
        except AssertionError as err:
            raise RuntimeError(COULD_NOT_SET.format(module='adsb', unit='status')) from err


@dataclass
class CSyncControl():
    __wifi:  Union[bool, None] = True
    __modem: Union[bool, None] = True

    @property
    def wifi(self) -> Union[bool, None]:
        return self.__wifi

    @property
    def modem(self) -> Union[bool, None]:
        return self.__modem

    @wifi.setter
    def wifi(self, p_state: Union[bool, None]) -> None:
        try:
            assert isinstance(p_state, Union[bool, None])
            self.__wifi = p_state
        except AssertionError as err:
            raise RuntimeError(COULD_NOT_SET.format(module='wifi', unit='state')) from err

    @modem.setter
    def modem(self, p_state: Union[bool, None]) -> None:
        try:
            assert isinstance(p_state, Union[bool, None])
            self.__modem = p_state
        except AssertionError as err:
            raise RuntimeError(COULD_NOT_SET.format(module='modem', unit='state')) from err

    def __str__(self) -> str:
        ret = {}
        if self.__modem is not None:
            ret['modem'] = self.__modem
        if self.__wifi is not None:
            ret['wifi'] = self.__wifi
        return ','.join([f"{k}:{v}" for k,v in ret.items()])

    def as_dict(self) -> dict:
        ret = {}
        if self.__modem is not None:
            ret['modem'] = self.__modem
        if self.__wifi is not None:
            ret['wifi'] = self.__wifi
        return ret


class CSingleton(object):
    _instances = {}

    def __new__(cls):
        if cls not in cls._instances:
            cls._instances[cls] = super(CSingleton, cls).__new__(cls)
        return cls._instances[cls] 


@dataclass
class CSyncObj(CSingleton):
    control:    CSyncControl    = CSyncControl()
    monitoring: CSyncMonitoring = CSyncMonitoring()
    adsb:       CSyncADSB       = CSyncADSB()
