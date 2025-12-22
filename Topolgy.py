

from mininet.topo import Topo

class MyTopo(Topo):
    def build(self):
        # إضافة 6 هوستس
        hosts = [self.addHost('h%d' % i, ip='10.0.0.%d' % i) for i in range(1, 7)]
        # إضافة 6 سويتشات
        switches = [self.addSwitch('s%d' % i) for i in range(1, 7)]

        # ربط كل هوست بالسويتش المقابل له
        for i in range(6):
            self.addLink(hosts[i], switches[i], bw=1000)

        # المسار الرئيسي (سلسلة: s1-s2-s3-s6)
        self.addLink(switches[0], switches[1], bw=1000) # s1-s2
        self.addLink(switches[1], switches[2], bw=1000) # s2-s3
        self.addLink(switches[2], switches[5], bw=1000) # s3-s6

        # المسارات البديلة (Alternate Paths)
        self.addLink(switches[0], switches[3], bw=1000) # s1-s4
        self.addLink(switches[3], switches[4], bw=1000) # s4-s5
        self.addLink(switches[4], switches[5], bw=1000) # s5-s6
        
        # وصلة إضافية لتعقيد الشبكة (s4-s6)
        self.addLink(switches[3], switches[5], bw=1000)

topos = {'mytopo': (lambda: MyTopo())}