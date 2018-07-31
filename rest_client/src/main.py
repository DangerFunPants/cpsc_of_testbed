import multipath_orchestrator as mp
import params as cfg



def main():
    # Create the route adder
    route_adder = mp.MPRouteAdder(cfg.of_controller_ip, 
        cfg.of_controller_port, cfg.route_path, cfg.seed_no)
    # Install all the static routes
    route_adder.install_routes()

   
if __name__ == '__main__':
    main()