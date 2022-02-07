from scapy.all import BitField, ByteField, IPField, FlagsField, Packet, ShortField

class RIP(Packet):
    name = "RIP"
    fields_desc = [
        ShortField("id", 1),                            # Same id as IP, 2 Bytes
        FlagsField("ipflags", 0, 3, ['R', 'DF','MF']),   # Same flags as IP, 3 bits
        BitField("ipfrag", 0, 13),                      # Same fragment offset as IP, 13 bits 
        ByteField("proto", 0),                       # Transport protocol inside RIP, 1 byte
        IPField("address", 0),                          # The address that mobile unit should respond to.
        BitField("mf", 0, 1),                           # More fragments flag for RIP payload, 1 bit
        BitField("frag", 0, 7)                          # Fragment offset for RIP payload, 7 bits
    ]