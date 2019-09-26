
import traceback                        as traceback
import networkx                         as nx
import time                             as time

import virtual_hosts.virtual_host       as virtual_host
import nw_control.topo_mapper           as topo_mapper
import attacker_tests.trials            as trials

SUBSTRATE_TOPOLOGY = nx.complete_graph(10)

def destroy_sender_receiver_pair(sender, receiver):
    if sender != None:
        sender.destroy_virtual_host()
    else:
        print("Refusing to destroy non-existent sender!")

    if receiver != None:
        receiver.destroy_virtual_host()
    else:
        print("Refusing to destroy non-existent receiver!")

def create_sender_receiver_pair(id_to_dpid):
    virtual_host_mac_address    = "00:02:00:00:00:%02d"
    actual_host_ip_address      = "192.168.1.%d"
    virtual_host_ip_address     = "10.10.0.%d"

    sender_host_id      = 1
    receiver_host_id    = 2

    sender_host = None
    receiver_host = None
    try:
        sender_host = virtual_host.PathHoppingSender.create_virtual_host(sender_host_id, 
                (virtual_host_mac_address % sender_host_id),
                (virtual_host_ip_address % sender_host_id),
                (actual_host_ip_address % sender_host_id),
                id_to_dpid[sender_host_id - 1])

        receiver_host = virtual_host.PathHoppingReceiver.create_virtual_host(receiver_host_id,
                (virtual_host_mac_address % receiver_host_id),
                (virtual_host_ip_address % receiver_host_id),
                (actual_host_ip_address % receiver_host_id),
                id_to_dpid[receiver_host_id - 1])
    except Exception as ex:
        destroy_sender_receiver_pair(sender_host, receiver_host)
        raise ex

    return sender_host, receiver_host

def conduct_path_hopping_trial(results_repository, the_trial):
    def stringify(value):
        return value if type(value) == str else str(value)

    def get_sender_kwargs(the_trial):
        sender_kwargs = { "port"            : the_trial.get_parameter("port")
                        , "K"               : the_trial.get_parameter("K")
                        , "N"               : the_trial.get_parameter("N")
                        , "data_file"       : the_trial.get_parameter("input-file")
                        , "message_size"    : the_trial.get_parameter("message-size")
                        , "timestep"        : the_trial.get_parameter("timestep")
                        , "hop_probability" : the_trial.get_parameter("lambda")
                        , "reliable"        : the_trial.get_parameter("reliable")
                        , "hop_method"      : the_trial.get_parameter("hop")
                        }
        sender_kwargs = {kw: stringify(arg) for kw, arg in sender_kwargs.items()}
        return sender_kwargs

    def get_receiver_kwargs(the_trial, sender_ip):
        receiver_kwargs = { "sender_ip"             : sender_ip
                          , "port"                  : the_trial.get_parameter("port")
                          , "data_file"             : the_trial.get_parameter("output-file")
                          , "timestep"              : the_trial.get_parameter("timestep")
                          , "hopping_probability"   : the_trial.get_parameter("lambda")
                          }
        receiver_kwargs = {kw: stringify(arg) for kw, arg in receiver_kwargs.items()}
        return receiver_kwargs

    sender, receiver = None, None
    try:
        id_to_dpid = topo_mapper.get_and_validate_onos_topo_x(SUBSTRATE_TOPOLOGY)

        sender, receiver = create_sender_receiver_pair(id_to_dpid)
        
        time.sleep(10)
        sender.start_path_hopping_sender(**get_sender_kwargs(the_trial))
        receiver.start_path_hopping_receiver(
                **get_receiver_kwargs(the_trial, sender.virtual_host_ip))
    
        print("Waiting on the receiver to terminate...")
        receiver.wait_until_done()
        print("Receiver has terminated.")
        # input("Stuff is happening. Hit return to continue...")
    except Exception as ex:
        traceback.print_exc()
        print(ex)
        input("Failed to carry out path hopping attacker test. Press enter to continue...")
    finally:
        destroy_sender_receiver_pair(sender, receiver)

def main():
    trial_provider = trials.test_with_single_trial()
    for the_trial in trial_provider:
        conduct_path_hopping_trial(None, the_trial)

if __name__ == "__main__":
    main()
