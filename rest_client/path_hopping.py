
import pprint                           as pp

import virtual_hosts.virtual_host       as virtual_host
import path_hopping.flow_allocation     as flow_allocation

def main():
    # virtual_host_one = virtual_host.VirtualHost.create_virtual_host("00:02:ca:fe:ba:be", 
    #         "10.10.0.1", "192.168.1.1", "of:000200fd457cff60")
    # virtual_host_two = virtual_host.VirtualHost.create_virtual_host("00:02:de:ad:be:ef", 
    #         "10.10.0.2", "192.168.1.2", "of:00073821c720c240")
    # input("Press enter to destroy virtual host...")
    # virtual_host_two.destroy_virtual_host()
    # virtual_host_one.destroy_virtual_host()
    flow_allocation.compute_flow_allocations()
    

if __name__ == "__main__":
    main()
