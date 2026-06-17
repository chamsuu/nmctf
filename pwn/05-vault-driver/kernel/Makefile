KVER    ?= 5.15.0
KDIR    ?= /lib/modules/$(KVER)/build
PWD     := $(shell pwd)

.PHONY: all clean

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean