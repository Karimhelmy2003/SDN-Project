from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpid_to_str
from pox.lib.recoco import Timer

log = core.getLogger()

MONITOR_INTERVAL = 5        # كل 5 ثواني
UTIL_THRESHOLD = 0.7        # 70%
ELEPHANT_THRESHOLD = 500    # Kbps
CONGESTION_CYCLES = 2       # دورتين متتاليتين

class SDNLoadBalancer(object):

    def __init__(self):
        core.openflow.addListeners(self)

        self.prev_stats = {}          # (dpid, port) -> bytes
        self.congestion_count = {}    # (dpid, port) -> count

        Timer(MONITOR_INTERVAL, self._request_stats, recurring=True)

    # ------------------ Monitoring Phase ------------------
    def _request_stats(self):
        for conn in core.openflow.connections.values():
            conn.send(of.ofp_stats_request(
                body=of.ofp_port_stats_request()
            ))

    # ------------------ Stats Handler ------------------
    def _handle_PortStatsReceived(self, event):
        dpid = event.connection.dpid

        for stat in event.stats:
            if stat.port_no >= of.OFPP_MAX:
                continue

            port_id = (dpid, stat.port_no)

            if port_id in self.prev_stats:
                byte_diff = stat.tx_bytes - self.prev_stats[port_id]

                # حساب السرعة
                speed_kbps = (byte_diff * 8) / (MONITOR_INTERVAL * 1024.0)

                # نفترض لينك 1Gbps
                utilization = speed_kbps / 1000000.0

                log.info(
                    "SW:%s Port:%s Utilization: %.2f%%",
                    dpid_to_str(dpid),
                    stat.port_no,
                    utilization * 100
                )

                # ---------------- Congestion Detection ----------------
                if utilization > UTIL_THRESHOLD:
                    self.congestion_count[port_id] = \
                        self.congestion_count.get(port_id, 0) + 1
                else:
                    self.congestion_count[port_id] = 0

                # ---------------- Rerouting Decision ----------------
                if self.congestion_count[port_id] >= CONGESTION_CYCLES:
                    if speed_kbps > ELEPHANT_THRESHOLD:
                        log.warning(
                            "Congestion Detected on %s Port %s",
                            dpid_to_str(dpid),
                            stat.port_no
                        )
                        self._reroute_elephant_flow(
                            event.connection,
                            stat.port_no
                        )

            self.prev_stats[port_id] = stat.tx_bytes

    # ------------------ Flow Rerouting ------------------
    def _reroute_elephant_flow(self, connection, in_port):
        msg = of.ofp_flow_mod()
        msg.priority = 100
        msg.match.in_port = in_port

        # مسار بديل (مثال أكاديمي)
        msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))

        msg.idle_timeout = 20
        msg.hard_timeout = 40

        connection.send(msg)

        log.info("Elephant flow rerouted proactively")

def launch():
    core.registerNew(SDNLoadBalancer)
