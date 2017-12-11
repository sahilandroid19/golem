import logging
import miniupnpc as miniupnpc
import pprint
from copy import deepcopy
from operator import concat
from typing import Dict

from golem.network.upnp.portmapper import IPortMapper

logger = logging.getLogger('golem.network.upnp')


class IGDPortMapper(IPortMapper):

    def __init__(self, discovery_delay: int = 200):
        """
        :param discovery_delay: IGD discovery delay in ms
        """
        self.upnp = miniupnpc.UPnP()
        self.upnp.discoverdelay = discovery_delay

        self._network = {
            'local_ip_address': None,
            'external_ip_address': None,
            'connection_type': None,
            'status_info': None
        }
        self._mapping = {
            'TCP': dict(),
            'UDP': dict()
        }
        self._available = None

    @property
    def available(self) -> bool:
        return self._available is True

    @property
    def mapping(self) -> Dict[str, Dict[int, int]]:
        return deepcopy(self._mapping)

    def discover(self):
        try:
            logger.info('Discovering IGD devices...')
            num_devices = self.upnp.discover()

            if not num_devices:
                raise RuntimeError("No IGD devices discovered")
            logger.info('Detected %u device(s)', num_devices)

            logger.info('Selecting an IGD device...')
            self.upnp.selectigd()

            network = self._gather_network_info()
            self._network.update(network)
        except Exception as exc:
            logger.warning('UPnP is not available: %r. This means that '
                           'automatic port forwarding is not possible.', exc)
            self._available = False
        else:
            logger.info('Network configuration:\n%r',
                        pprint.pformat(self._network))
            self._available = True

    def create_mapping(self,
                       local_port: int,
                       external_port: int = None,
                       protocol: str = 'TCP',
                       lease_duration: int = None):

        if self._available is None:
            self.discover()
        self._assert_available()

        preferred_port = external_port or local_port
        local_ip = self._network['local_ip_address']
        lease = str(lease_duration) if lease_duration else ''

        try:
            external_port = self._find_free_port(preferred_port, protocol)
            description = 'Golem[{}]'.format(external_port)

            result = self.upnp.addportmapping(
                external_port, protocol,
                local_ip, local_port,
                description, lease
            )
            error = 'Unknown error'
        except Exception as exc:
            result = None
            error = exc

        if result:
            mapping = self._mapping[protocol.upper()]
            mapping[local_port] = external_port
        else:
            logger.warning('Cannot map port %u (%s): %r',
                           local_port, protocol, error)

    def remove_mapping(self, external_port: int, protocol: str):
        try:
            result = self.upnp.deleteportmapping(external_port, protocol)
            error = 'Mapping does not exist'
        except Exception as exc:
            result = None
            error = exc

        if result:
            logger.info('External port %u (%s) mapping removed',
                        external_port, protocol)
        else:
            logger.warning('Cannot remove external port %u (%s) mapping: %r',
                           external_port, protocol, error)

    def quit(self):
        if not self.available:
            return

        for protocol, mapping in self._mapping.items():
            for external_ip in mapping.values():
                self.remove_mapping(external_ip, protocol)

    def _find_free_port(self, preferred_port: int, protocol: str):
        range_1 = (preferred_port, 65536)
        range_2 = (1, preferred_port)

        for port in concat(range_1, range_2):
            result = self.upnp.getspecificportmapping(port, protocol)
            if result:
                return port

        raise RuntimeError("No free external ports are available")

    def _gather_network_info(self):
        return {
            'local_ip_address': self.upnp.lanaddr,
            'external_ip_address': self.upnp.externalipaddress(),
            'connection_type': self.upnp.connectiontype(),
            'status_info': self.upnp.statusinfo()
        }

    def _assert_available(self):
        if not self._available:
            raise RuntimeError('PortMapper is not available')