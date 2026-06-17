.PHONY: all clean rootfs module

all: rootfs

rootfs:
	cd rootfs && bash build_rootfs.sh

module:
	cd kernel && make

# Skip module build by default - requires kernel headers
# cd kernel && make -C /lib/modules/$(KVER)/build M=$(PWD) modules

clean:
	rm -f dist/rootfs.cpio.gz