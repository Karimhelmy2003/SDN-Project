from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpid_to_str
from pox.lib.recoco import Timer

log = core.getLogger()

class Monitor(object):
    def __init__(self):
        core.openflow.addListeners(self)
        self.prev_stats = {} 
        Timer(5, self._send_stats_request, recurring=True)

    def _send_stats_request(self):
        for connection in core.openflow.connections.values():
            connection.send(of.ofp_stats_request(body=of.ofp_port_stats_request()))

    def _handle_PortStatsReceived(self, event):
        dpid = dpid_to_str(event.connection.dpid)
        for stat in event.stats:
            if stat.port_no < of.OFPP_MAX:
                port_id = (event.connection.dpid, stat.port_no)
                
                if port_id in self.prev_stats:
                    byte_diff = stat.tx_bytes - self.prev_stats[port_id]
                    speed_Kbps = (byte_diff * 8) / (5 * 1024.0)
                    
                    log.info("SW: %s | Port: %s | Speed: %.2f Kbps", dpid, stat.port_no, speed_Kbps)
                    
                    # شرط الـ Rerouting: إذا زادت السرعة عن 500 ك.بت
                    if speed_Kbps > 500:
                        log.warning("!!! Congestion Detected on %s Port %s !!!", dpid, stat.port_no)
                        log.info("Action: Rerouting traffic to alternative path...")
                        
                        # إرسال أمر للسويتش لإغلاق هذا المسار المزدحم (Flow Mod)
                        msg = of.ofp_flow_mod()
                        msg.match.in_port = stat.port_no
                        msg.priority = 65535 # أولوية قصوى
                        msg.actions = [] # مصفوفة فارغة تعني Drop (إجبار الشبكة على البحث عن مسار بديل)
                        msg.idle_timeout = 10 # سيتم العودة للمسار الأصلي بعد 10 ثواني من الهدوء
                        event.connection.send(msg)
                
                self.prev_stats[port_id] = stat.tx_bytes

def launch():
    core.registerNew(Monitor)