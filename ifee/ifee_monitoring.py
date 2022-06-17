import asyncio
from prometheus_client import Metric, write_to_textfile, CollectorRegistry
from ifee.ifee_common import CSyncObj


class CAircraftCollector():
    def __init__(self) -> None:
        super().__init__()
        self.__status = CSyncObj()

    def collect(self) -> None:
        metrics = self.__status.monitoring.as_dict()

        if not self.__status.adsb.icao:
            return None

        metric_vel = Metric('velocity', 'Aircraft Velocity', 'gauge')
        metric_vel.add_sample('velocity', value=int(metrics['velocity']), labels={'icao': self.__status.adsb.icao})
        yield metric_vel

        metric_alt = Metric('altitude', 'Aircraft Altitude', 'gauge')
        metric_alt.add_sample('altitude', value=int(metrics['altitude']), labels={'icao': self.__status.adsb.icao})
        yield metric_alt

        if metrics['position']['lat'] and metrics['position']['lon']:
            metric_lat = Metric('latitude', 'Aircraft Latitude', 'gauge')
            metric_lat.add_sample('latitude',
                                  value=metrics['position']['lat'],
                                  labels={'icao': self.__status.adsb.icao}
                                )
            yield metric_lat

            metric_lan = Metric('longitude', 'Aircraft Longitude', 'gauge')
            metric_lan.add_sample('longitude',
                                  value=metrics['position']['lon'],
                                  labels={'icao': self.__status.adsb.icao}
                                )
            yield metric_lan


async def collect_aircraft(p_file_path: str = '/var/lib/prom/aircraft.prom') -> None:
    while True:
        try:
            registry = CollectorRegistry()
            registry.register(CAircraftCollector())
            write_to_textfile(p_file_path, registry)
            await asyncio.sleep(10)
        except PermissionError as err:
            raise RuntimeError(f"[prom] {str(err)}")


class CMetricCollector():
    def __init__(self) -> None:
        super().__init__()
        self.__status = CSyncObj()

    def collect(self) -> None:
        metrics = self.__status.monitoring.as_dict()

        metric_dc = Metric('dc_status', 'DC adapter status', 'gauge')
        metric_dc.add_sample('dc_status', value=metrics['powerunit'], labels={})
        yield metric_dc

        metric_bl = Metric('bat_level', 'Battery capacity level', 'gauge')
        for bat in metrics['batteries']:
            metric_bl.add_sample('bat_level', labels={'bat_num': str(bat['index'])}, value=int(bat['level']))
        yield metric_bl

        metric_bp = Metric('bat_power', 'Battery power level', 'gauge')
        for bat in metrics['batteries']:
            metric_bp.add_sample('bat_power', labels={'bat_num': str(bat['index'])}, value=int(bat['power']))
        yield metric_bp

        metric_tp = Metric('temperature', 'Temperature', 'gauge')
        for tmp in metrics['temperature']:
            metric_tp.add_sample('temperature', labels={'unit': tmp['name']}, value=tmp['value'])
        yield metric_tp


async def collect_metrics(p_file_path: str = '/var/lib/prom/kontron.prom') -> None:
    while True:
        try:
            registry = CollectorRegistry()
            registry.register(CMetricCollector())
            write_to_textfile(p_file_path, registry)
            await asyncio.sleep(10)
        except PermissionError as err:
            raise RuntimeError(f"[prom] {str(err)}")
