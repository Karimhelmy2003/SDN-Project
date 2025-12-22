from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpid_to_str
from pox.lib.recoco import Timer

log = core.getLogger()

class Monitor(object):
    def __init__(self):
        # تسجيل المستمعين لأحداث OpenFlow
        core.openflow.addListeners(self)
        # قاموس لتخزين إحصائيات البايتات السابقة لكل منفذ
        self.prev_stats = {} 
        # إنشاء مؤقت لطلب الإحصائيات من السويتشات كل 5 ثوانٍ
        Timer(5, self._send_stats_request, recurring=True)

    def _send_stats_request(self):
        # إرسال طلب Port Stats لجميع السويتشات المتصلة بالكنترولر
        for connection in core.openflow.connections.values():
            connection.send(of.ofp_stats_request(body=of.ofp_port_stats_request()))

    def _handle_PortStatsReceived(self, event):
        # تحويل معرف السويتش (DPID) إلى نص مقروء
        dpid = dpid_to_str(event.connection.dpid)
        for stat in event.stats:
            # تجاهل المنافذ الوهمية والتركيز على المنافذ الفيزيائية
            if stat.port_no < of.OFPP_MAX:
                # إنشاء معرف فريد يجمع بين السويتش ورقم المنفذ
                port_id = (event.connection.dpid, stat.port_no)
                
                # التحقق مما إذا كان لدينا قراءة سابقة لهذا المنفذ
                if port_id in self.prev_stats:
                    # حساب الفرق في عدد البايتات المرسلة
                    byte_diff = stat.tx_bytes - self.prev_stats[port_id]
                    # تحويل الفرق إلى سرعة بالكيلوبت في الثانية (Kbps)
                    # المعادلة: (البايتات * 8 بت) / (5 ثوانٍ * 1024)
                    speed_Kbps = (byte_diff * 8) / (5 * 1024.0)
                    
                    # طباعة تقرير السرعة في شاشة الكنترولر (الأسبوع الخامس)
                    log.info("SW: %s | Port: %s | Traffic: %.2f Kbps", dpid, stat.port_no, speed_Kbps)
                    
                    # اكتشاف الازدحام (الأسبوع السادس): إذا تجاوزت السرعة 500 Kbps
                    if speed_Kbps > 500:
                        log.warning("High congestion on %s port %s", dpid, stat.port_no)
                
                # تحديث القيمة السابقة لاستخدامها في الدورة القادمة
                self.prev_stats[port_id] = stat.tx_bytes

def launch():
    # تسجيل الموديول في نظام POX عند التشغيل
    core.registerNew(Monitor)