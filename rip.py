from scapy.all import BitField, ByteField, IPField, FlagsField, Packet, ShortField

class RIP(Packet):
    name = "RIP"
    fields_desc = [
        ShortField("id", 1),                            # Same id as IP, 2 Bytes
        BitField("mf", 0, 1),                           # More fragments flag for RIP payload, 1 bit
        BitField("frag", 0, 7)                          # Fragment offset for RIP payload, 7 bits
    ]