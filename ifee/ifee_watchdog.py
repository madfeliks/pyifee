import asyncio
from logging import getLogger
import ping3
from ping3 import ping
from ifee.ifee_dbus import CConnection, CModemManager, CNetworkManager
from ifee.ifee_common import CSyncObj


logger = getLogger("[watchdog]")


async def activate_conn(p_conn: CConnection, p_ping_host: str, p_wait_delay: int) -> bool:
    try:
        p_conn.connect = True
        while not p_conn.connect:
            await asyncio.sleep(p_wait_delay)
    except RuntimeError:
        msg = f"[watchdog] activate {str(p_conn)} connection failed"
        logger.error(msg)
        return False

    for _ in range(3):
        try:
            ping_res = ping(p_ping_host, timeout=1)
            msg = f"ping {p_ping_host} successfull: {float(ping_res)}"
            logger.debug(msg)
            return True
        except (ping3.errors.PingError, PermissionError, OSError) as err:
            msg = f"ping {p_ping_host} failed: {str(err)}"
            logger.error(msg)
            await asyncio.sleep(p_wait_delay)

    return False


async def watch_dog(p_modem: int, p_lte: str, p_vpn: str, p_lte_host: str, p_vpn_host: str) -> None:
    logger.debug("started")
    ping3.EXCEPTIONS = True

    m_manager = CModemManager()
    n_manager = CNetworkManager()

    status = CSyncObj()

    wait_delay = 5
    loop_delay = 1

    try:
        while True:
            lte = n_manager.get(p_lte)
            vpn = n_manager.get(p_vpn)
            modems = m_manager.modems

            if not lte:
                raise RuntimeError("[watchdog] lte connection does not exist")
            if not vpn:
                raise RuntimeError("[watchdog] vpn connection does not exist")

            if len(modems) == 0:
                logger.error("no one modems have not been found")
                await asyncio.sleep(wait_delay)
                continue

            modem = next((m for m in modems if m.index == p_modem), modems[0])
            modem.connection = p_lte

            check = (status.adsb.active, status.control.modem)
            msg = f"state -- ADS-B: {check[0]}, control: {check[1]}"
            logger.debug(msg)

            match check:
                case (True, True):
                    modem.enable()

                    activate = await activate_conn(lte, p_lte_host, wait_delay)
                    if not activate:
                        modem.disable()
                        continue

                    activate = await activate_conn(vpn, p_vpn_host, wait_delay)
                    if not activate:
                        modem.disable()
                        continue
                case _:
                    vpn.connect = False
                    await asyncio.sleep(wait_delay)

                    lte.connect = False
                    await asyncio.sleep(wait_delay)

                    modem.disable()

            await asyncio.sleep(loop_delay)
    except(asyncio.CancelledError, KeyboardInterrupt, SystemExit):
        logger.info("stopped")
