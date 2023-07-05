import os
import mmap
import struct


class Bar(object):
    """ Create a Bar instance that ``mmap()`` s a PCIe device BAR.

    :param str filename: sysfs filename for the corresponding resourceX file.

    """

    def __init__(self, filename):
        self.__mmio = None  # mmio mapped space
        self.__stat = os.stat(filename)
        fd = os.open(filename, os.O_RDWR)
        self.__mmio = mmap.mmap(fd, 0, prot=mmap.PROT_READ | mmap.PROT_WRITE)
        os.close(fd)

    def __del__(self):
        if self.__mmio is not None:
            self.__mmio.close()

    def __fix_offset(self, offset):
        """assume given `offset` is dword based index, now fix it to
        byte based index.

        """
        if offset < 0:
            raise ValueError("invalid access to offset %d" % offset)

        offset = offset << 2
        if offset + 3 > self.size:
            raise ValueError("offset (0x%x) exceeds BAR size (0x%x)" %
                             (offset, self.size))
        return offset

    def read(self, offset, ndword=1):
        """ Read a 32 bit / double word value from offset.

        :param int offset: BAR byte offset to read from.
        :param int nword: number of words to read with `offset` as base.
        :returns: Double word read from the given BAR offset.
        :rtype: double word / 32 bit unsigned long / int

        """
        offset = self.__fix_offset(offset)

        # read single dword
        if ndword == 1:
            reg = self.__mmio[offset: offset + 4]
            return struct.unpack("<L", reg)[0]

        # read multiple continuous dwords
        dwords = []
        while ndword > 0:
            reg = self.__mmio[offset:offset + 4]
            dwords.append(struct.unpack("<L", reg)[0])
            offset += 4
            ndword -= 1
        return dwords

    def write(self, offset, dwords):
        """ Write a 32 bit / double word value to offset.

        :param int offset: BAR byte offset to write to.
        :param int data: double word to write to the given BAR offset.
        """
        offset = self.__fix_offset(offset)
        self.__mmio.seek(offset, os.SEEK_SET)
        if isinstance(dwords, (list, tuple)):
            for dword in dwords:
                # pack dword data
                reg = struct.pack("<L", dword)
                # write to map. no ret. check: ValueError/TypeError is raised on error
                self.__mmio.write(reg)
                # Flush current page for immediate update.
                page_offset = offset & (~(mmap.PAGESIZE - 1) & 0xffffffff)
                self.__mmio.flush(page_offset, mmap.PAGESIZE)
                offset += 4
        else:
            reg = struct.pack("<L", dwords)
            # write to map. no ret. check: ValueError/TypeError is raised on error
            self.__mmio.write(reg)
            # Flush current page for immediate update.
            page_offset = offset & (~(mmap.PAGESIZE - 1) & 0xffffffff)
            self.__mmio.flush(page_offset, mmap.PAGESIZE)
        # TODO: check return value, only for >=Python3.8

    @property
    def size(self):
        """
        Get the size of the BAR.

        :returns: BAR size in bytes.
        :rtype: int
        """
        return self.__stat.st_size
