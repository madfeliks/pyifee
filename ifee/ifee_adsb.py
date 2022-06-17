from dataclasses import dataclass
from typing import Union
import json
import asyncio
from logging import getLogger
import requests
import pyModeS as pms
from ifee.ifee_common import CSyncObj, CPosition


@dataclass
class CMessageADSB():
    __msg: str
    __ts: int

    @property
    def msg(self) -> str:
        return self.__msg

    @property
    def time(self) -> int:
        return self.__ts


def get_icao_from_ground(p_box_id: str, p_url: str, p_user: str, p_pass: str) -> Union[str, None]:
    url = '/'.join([p_url, 'api/authenticate'])
    headers = {'Content-Type': 'application/json'}
    data = f'{{"username": "{p_user}", "password": "{p_pass}"}}'
    try:
        res = requests.post(url=url, data=data, headers=headers, timeout=10)
        if res.ok:
            token = res.json()['token']
        else:
            return None
    except(requests.exceptions.RequestException, json.decoder.JSONDecodeError) as error:
        raise RuntimeError(f"[get_icao_from_ground] {str(error)}") from error

    url = '/'.join([p_url, 'api/admin/box/serial', p_box_id])
    headers = {'Content-Type': 'application/json', 'Authorization': ' '.join(['Bearer', token])}
    try:
        res = requests.get(url=url, headers=headers, timeout=10)
        if res.ok:
            ret = res.json()['hex']
        else:
            return None
    except(requests.exceptions.RequestException, json.decoder.JSONDecodeError) as error:
        raise RuntimeError(f"[get_icao_from_ground] {str(error)}") from error

    return ret


async def parse_adsb() -> None:
    status = CSyncObj()

    logger = getLogger("[ads-b]")
    logger.debug("started")

    msg0 = None
    msg1 = None

    if not status.adsb.icao:
        return None

    try:
        while True:
            if status.adsb.msg.qsize() == 0:
                await asyncio.sleep(1)
                continue

            msg = status.adsb.msg.get_nowait()
            logger.debug("parse new ads-b message: %s", msg.msg)

            velocity = 0
            altitude = 0
            position = None
            typecode = None

            time_stamp = msg.time
            message = msg.msg

            icao = pms.adsb.icao(message)
            typecode = pms.adsb.typecode(message)

            if icao != status.adsb.icao:
                await asyncio.sleep(1)
                continue

            if typecode == 19 or (4 < typecode < 9):
                velocity = pms.adsb.velocity(message)[0]
                status.monitoring.vel = velocity
                logger.info("ts: %i -- msg: %s -- icao: %s -- vel: %i", time_stamp, message, icao, velocity)

                match (bool(velocity >= 160), status.adsb.active):
                    case (True, True):
                        status.adsb.active = False
                        logger.info("speed >= 160kt -- set lte status to watchdog: disabled")
                    case (False, False):
                        status.adsb.active = True
                        logger.info("speed < 160kt  -- set lte status to watchdog: enabled")
                    case _:
                        pass

            elif (9 <= typecode <= 18) or (20 <= typecode <= 22):
                if pms.adsb.oe_flag(message):
                    msg1 = message
                    time_stamp_1 = time_stamp
                else:
                    msg0 = message
                    time_stamp_0 = time_stamp

                if msg0 and msg1:
                    position = pms.bds.bds05.airborne_position(msg0, msg1, time_stamp_0, time_stamp_1)
                    altitude = pms.adsb.altitude(message)
                    msg0 = None
                    msg1 = None
                    status.monitoring.pos = CPosition(position[0],position[1])
                    status.monitoring.alt = altitude
                    logger.info("ts: %i -- msg: %s -- icao: %s -- pos: %s -- alt: %i", time_stamp, message, icao, str(position), int(altitude))

            await asyncio.sleep(1)
    except(asyncio.CancelledError, KeyboardInterrupt, SystemExit):
        logger.info("stopped")
