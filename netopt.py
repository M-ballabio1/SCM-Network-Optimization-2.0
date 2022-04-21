# ==============================================================================
# description     :Optimization models for teaching purposes
# author          :Roberto Pinto
# date            :2022.04.21
# version         :1.2
# notes           :This software is meant for teaching purpose only and it is provided as-is under the GPL license.
#                  The models are inspired by the book Watson, M., Lewis, S., Cacioppi, P., Jayaraman, J. (2013)
#                  Supply Chain Network Design, Pearson. 
#                  http://networkdesignbook.com/
#                  All the data has been taken from the book.
#                  The software is provided as-is, with no guarantee by the author.
# ==============================================================================

import pulp as pl
import pandas as pd
import matplotlib.pyplot as plt
import pprint

dpi = 136
fig_x = 8
fig_y = 5

def print_dict(data):
    """ PrettyPrint the data """
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(data)


def print_solution(data):
    """ Print some details of the solution"""
    print_dict(data)


def netopt(num_warehouses=3,
           warehouses=None,
           customers=None,
           distance=None,
           distance_ranges=None,
           objective="",
           high_service_distance=None,
           avg_service_distance=None,
           max_service_distance=None,
           force_open=None,
           force_closed=None,
           force_single_sourcing=True,
           force_uncapacitated=False,
           force_allocations=None,
           ignore_fixed_cost=False,
           plot=True,
           hide_inactive=False,
           solver_log=False,
           unit_transport_cost=0.1,
           **kwargs):
    """ Defines the optimal location of warehouses choosing from a set of candidate locations
        The objective is defined by the <objective> parameter, which can be either "maxcover", "mindistance" or "mincost".
        :param num_warehouses: number of warehouses to activate (integer number > 0)
        :param warehouses: list of candidate locations (list of Warehouse)
        :param customers: list of customer locations (list of Customer)
        :param distance: distance matrix
        :param distance_ranges: list of distances to compute the % of demand at different distances. For example, if distance_ranges = [0, 100, 200] the model returns the percentage of demand in the ranges [0, 100], (100, 200], (200, 99999], where 99999 is used to represent a very long distance (i.e. infinite distance).
        :param objective: objective function to optimize. Can be "maxcover" (maximizes the demand covered), "mindistance" (minimizes the average weighted distance) or "mincost" (minimizes the sum transportation and fixed cost)
        :param high_service_distance: distance range within which the demand covered must be maximized
        :param avg_service_distance: largest average weighted distance tolerated. This is used to limit the effect of random allocations of customers not contributing to the maxcover objective
        :param max_service_distance: all customers must have a warehouse within this distance
        :param force_open: list of warehouse that are forced to be open. Use the ID of the warehouses (see show_data function) to specify the open ones
        :param force_closed: list of warehouse that are forced to be closed. Use the ID of the warehouses (see show_data function) to specify the closed ones
        :param force_single_sourcing: if True, forces the customers to have one single supplier.
        :param force_uncapacitated: if True, the problem is solved without considering the capacities of the warehouse
        :param force_allocations: list of pairs (warehouse_id, customer_id) forcing a warehouse to serve a customer. For example, [(1, 2), (1, 6)] forces the warehouse with id 1 to serve the customers with id 2 and 6
        :param ignore_fixed_cost: if True, ignore the fixed cost in the objective function. This is used only for the "mincost" objective
        :param plot: if True, plot the final solution
        :param hide_inactive: if True, hides the inactive warehouses in the plot of the final solution
        :param solver_log: if True, shows the log of the solver
        :param unit_transport_cost: transportation cost per km and unit of product
        :param warehouse_active_marker: shape of the active warehouse icons; allowed values are s=square, o=circle, *=star, ^=triangle, v=inverted triangle
        :param warehouse_active_markercolor: color of the active warehouse icons. Allowed values are red, green, blue, black, yellow
        :param warehouse_active_markersize: size of the active warehouse icons
        :param warehouse_marker: shape of the warehouse icons; allowed values are s=square, o=circle, *=star, ^=triangle, v=inverted triangle
        :param warehouse_markercolor: color of the warehouse icons. Allowed values are red, green, blue, black, yellow
        :param warehouse_markersize: size of the warehouse icons
        :param customer_multisourced_marker: shape of the multisourced customer icons; allowed values are s=square, o=circle, *=star, ^=triangle, v=inverted triangle
        :param customer_multisourced_markercolor: color of the multisourced customer icons. Allowed values are red, green, blue, black, yellow
        :param customer_multisourced_markersize: size of the multisourced customer icons
        :param customer_marker: shape of the customer icons; allowed values are s=square, o=circle, *=star, ^=triangle, v=inverted triangle
        :param customer_markercolor: color of the customer icons. Allowed values are red, green, blue, black, yellow
        :param customer_markersize: size of the customer icons        
        :return: the solution of the model or infeasible
        """

    # check input
    print('CHECK INPUTS...', end="")
    if not objective:
        print('Please, specify an objective between maxcover (maximise the demand within <high_service_distance>) and mindist (minimize weighted average distance)')
        return None
    if objective not in ['maxcover', 'mindistance', 'mincost']:
        print('Please, specify an objective between maxcover (maximise the demand within <high_service_distance>) and mindist (minimize weighted average distance)')
        return None

    if not warehouses or not customers or not distance:
        print('At least one required parameter is missing')
        print('REQUIRED PARAMETERS: warehouses, customers, distance')
        return None
    if not distance_ranges:
        distance_ranges = [0]

    if distance_ranges[0] != 0:
        distance_ranges.insert(0, 0)

    if distance_ranges[-1] != 99999:
        distance_ranges.append(99999)

    if not max_service_distance:
        max_service_distance = 99999

    if not type(unit_transport_cost) == float:
        raise Exception(f'unit_transport_cost must be a float, {unit_transport_cost} given')

    # check if values in distance_ranges are increasing
    if not all([True if y-x > 0 else False for (x, y) in zip(distance_ranges, distance_ranges[1:])]):
        print('ERROR: distance_ranges parameters must contains values in strictly ascending order')
        return None
    print('OK')

    print('BUILD MODEL...', end="")
    # define the problem container

    if objective == 'maxcover':
        pb = pl.LpProblem("NetworkOptimizationModel", pl.LpMaximize)
    elif objective in ['mindistance', 'mincost']:
        pb = pl.LpProblem("NetworkOptimizationModel", pl.LpMinimize)

    warehouses_id = set(warehouses.keys())
    customers_id = set(customers.keys())

    # define variables

    # Customers assignment to warehouses
    if force_single_sourcing:
        assignment_vars = pl.LpVariable.dicts(name="Flow",
                                    indices=[(w, c) for w in warehouses_id for c in customers_id],
                                    lowBound=0,
                                    upBound=1,
                                    cat=pl.LpInteger)

    else:
        assignment_vars = pl.LpVariable.dicts(name="Flow",
                                            indices=[(w, c) for w in warehouses_id for c in customers_id],
                                            lowBound=0.0,
                                            upBound=1.0,
                                            cat=pl.LpContinuous)
    # Open warehouses
    facility_status_vars = pl.LpVariable.dicts(name="Open",
                                               indices=[w for w in warehouses_id],
                                               lowBound=0,
                                               upBound=1,
                                               cat=pl.LpInteger)
    
    # Setting the value to 1 if customer c is within the given high service distance of warehouse w
    if high_service_distance:
        high_service_dist_par = {(w, c): 1 if distance[w, c] <= high_service_distance else 0 for w in warehouses_id for c in customers_id}
    else:
        high_service_dist_par = {(w, c): 1 for w in warehouses_id for c in customers_id}

    # Setting the value to 1 if customer c is within the given max service distance of warehouse w
    if max_service_distance:
        max_service_dist_par = {(w, c): 1 if distance[w, c] <= max_service_distance else 0 for w in warehouses_id for c in customers_id}
    else:
        max_service_dist_par = {(w, c): 1 for w in warehouses_id for c in customers_id}

    # setting problem objective
    if objective == 'maxcover':
        # define the objective function (sum of all covered demand within <high_service_dist_par> distance)
        total_covered_demand_high_service = pl.lpSum([customers[c].demand * high_service_dist_par[w, c] * assignment_vars[w, c] 
                                                      for w in warehouses_id for c in customers_id]) / pl.lpSum([customers[c].demand for c in customers_id])
        pb.setObjective(total_covered_demand_high_service)
    elif objective == 'mindistance':
        # define the objective function (sum of all production costs)
        total_weighted_distance = pl.lpSum([customers[c].demand * distance[w, c] * assignment_vars[w, c] 
                                            for w in warehouses_id for c in customers_id]) / pl.lpSum([customers[c].demand for c in customers_id])
        pb.setObjective(total_weighted_distance)
    elif objective == 'mincost':
        total_cost = pl.lpSum([unit_transport_cost * customers[c].demand * distance[w, c] * assignment_vars[w, c] 
                               for w in warehouses_id for c in customers_id])

        if not ignore_fixed_cost:
            total_cost += pl.lpSum([warehouses[w].fixed_cost * facility_status_vars[w]
                                    for w in warehouses_id])

        pb.setObjective(total_cost)
    else:
        print(f'Objective {objective} not recognized')
        return None

    # set constraints
    for c in customers_id:
        pb += pl.LpConstraint(e = pl.lpSum([assignment_vars[w, c] for w in warehouses_id]), 
                              sense=pl.LpConstraintEQ, 
                              rhs=1,
                              name=f"Customer_{c}_Served")

    pb += pl.LpConstraint(e = pl.lpSum([facility_status_vars[w] for w in warehouses_id]),
                          sense=pl.LpConstraintEQ,
                          rhs=num_warehouses,
                          name=f"Num_of_active_warehouses")
    
    for w in warehouses_id:
        for c in customers_id:
            pb += pl.LpConstraint(e = assignment_vars[w, c] - facility_status_vars[w],
                                  sense=pl.LpConstraintLE,
                                  rhs=0,
                                  name=f"Logical_constraint_between_customer_{c}_and_warehouse_{w}")
    
    # Limit the average service distance to avoid random allocation of customer beyond the <high_service_distance> range
    if avg_service_distance:
        pb += pl.LpConstraint(e=pl.lpSum([distance[w, c] * customers[c].demand * assignment_vars[w, c] for w in warehouses_id for c in customers_id]) / pl.lpSum([customers[c].demand for c in customers_id]),
                              sense=pl.LpConstraintLE,
                              rhs=avg_service_distance,
                              name='Avoid_random_allocations' )

    # Add capacity limits to warehouses
    for w_id, w in warehouses.items():
        if w.capacity and not force_uncapacitated:
            pb += pl.LpConstraint(e=pl.lpSum([customers[c].demand * assignment_vars[w_id, c] for c in customers_id]),
                                  sense=pl.LpConstraintLE,
                                  rhs=w.capacity,
                                  name=f'Capacity_limit_warehouse_{w_id}')

    # Forbid assignment to warehouses farther than <max_service_distance>. This may lead to infeasibility
    for w in warehouses_id:
        for c in customers_id:
            assignment_vars[w, c].upBound = max_service_dist_par[w, c]

    # Force open warehouses
    if force_open and isinstance(force_open, list):
        print(f'Forcing open warehouses: {force_open}')
        for w in force_open:
            try:
                facility_status_vars[w].lowBound = 1
            except KeyError:
                print(f'Warehouse {w} does not exist')

    # Force closed warehouses
    if force_closed and isinstance(force_closed, list):
        print(f'Forcing closed warehouses: {force_closed}')
        for w in force_closed:
            try:
                facility_status_vars[w].upBound = 0
            except KeyError:
                print(f'Warehouse {w} does not exist')

    # Force allocations
    if force_allocations and isinstance(force_allocations, list):
        try:
            for each in force_allocations:
                assignment_vars[each[0], each[1]].lowBound = 1
                assignment_vars[each[0], each[1]].upBound = 1
        except KeyError:
            pass

    print('OK')
    
    # The problem is solved using PuLP's choice of Solver
    print('SOLVE...', end="")
    _solver = pl.PULP_CBC_CMD(keepFiles=False,
                              gapRel=0.00,
                              timeLimit=120, 
                              msg=solver_log)
    pb.solve(solver=_solver)
    print('OK')

    print("Optimization Status ", pl.LpStatus[pb.status] ) #print in Jupyter Notebook
    if pl.LpStatus[pb.status] == "Infeasible" :
        print("********* ERROR: Model not feasible, don't use results.")

    # print objective
    flows = {(w, c) for w in warehouses_id for c in customers_id if assignment_vars[w, c].varValue > 0}
    
    active_warehouses = {w for w in warehouses_id if facility_status_vars[w].varValue == 1}
    
    if objective == 'maxcover':
        perc_covered_demand_high_service = pl.value(pb.objective)
        print(f'% covered demand within {high_service_distance} distance: {round(perc_covered_demand_high_service * 100, 1)}%')
    elif objective == 'mindistance':
        avg_weighted_distance = pl.value(pb.objective)
        print(f'Average weighted distance: {round(avg_weighted_distance, 0)}')
    elif objective == 'mincost':
        print(f'Total cost: {round(pl.value(pb.objective), 0)}')
        print('Cost splitting:')
        print(f'- Transportation cost: {round(sum([unit_transport_cost * customers[c].demand * distance[w, c] * assignment_vars[w, c].varValue for w in warehouses_id for c in customers_id]), 0)}')

        if not ignore_fixed_cost:
            print(f'- Yearly fixed cost: {round(sum([warehouses[w].fixed_cost * facility_status_vars[w].varValue for w in warehouses_id]), 0)}')
        else:
            print('Forced ignoring fixed cost')            
    else:
        print(f'Objective {objective} not recognized')
        return None

    print()
    print(f'Open warehouses:')
    total_outflow = 0.
    for w in active_warehouses:
        try:
            outflow = sum([customers[c].demand * assignment_vars[w, c].varValue for c in customers_id])
        except TypeError:
            outflow = 0

        total_outflow += outflow            
        
        try:
            assigned_customers = int(sum([1 if assignment_vars[w, c].varValue > 0. else 0 for c in customers_id ]))
        except TypeError:
            assigned_customers = 0

        print(f'ID: {w:3} City: {warehouses[w][1]:20} State: {warehouses[w][2]:6} Num. customers: {assigned_customers:3}  Outflow: {outflow:11} units')
    print()
    print(f'Total outflow: {total_outflow} units')
    
    customers_assignment = []
    for (w, c) in assignment_vars.keys():
        if assignment_vars[(w, c)].varValue > 0:
            cust = {
                'Warehouse':str(warehouses[w].city) + ', ' + str(warehouses[w].state),
                'Customer':str(customers[c].city) + ', ' + str(customers[c].state),
                'Customer Demand': customers[c].demand,
                'Distance': distance[w,c],
                'Warehouse Latitude' : warehouses[w].latitude,
                'Warehouse Longitude' : warehouses[w].longitude,
                'Customers Latitude' : customers[c].latitude,
                'Customers Longitude': customers[c].longitude
            }
            customers_assignment.append(cust)
                  
    df_cu = pd.DataFrame.from_records(customers_assignment)
    df_cu = df_cu[['Warehouse', 'Customer', 'Distance', 'Customer Demand']]    
    labels = list(range(1, len(distance_ranges)))
    df_cu['distance_range'] = pd.cut(df_cu['Distance'], 
                                     bins=distance_ranges,
                                     labels=labels,
                                     include_lowest=True)
    
    total_demand = sum(df_cu['Customer Demand'])
    demand_perc_by_ranges = {}
    for band in labels:
        perc_of_demand_in_band = sum(df_cu[df_cu['distance_range'] == band]['Customer Demand']) / total_demand
        distance_range_lower_limit = distance_ranges[band-1]
        distance_range_upper_limit = distance_ranges[band]
        print(f'% of demand in range {distance_range_lower_limit:5} - {distance_range_upper_limit:5}: {round(perc_of_demand_in_band * 100, 1):>3}')
        demand_perc_by_ranges[(distance_range_lower_limit, distance_range_upper_limit)] = perc_of_demand_in_band

    print(f"Most distant customer is at {df_cu['Distance'].max()}")
    print(f"Average customers distance (no weights): {df_cu['Distance'].mean()}")    

    df_cu['Weighted_Distance'] = df_cu['Distance'] * df_cu['Customer Demand']
    avg_weighted_distance = df_cu['Weighted_Distance'].sum() / df_cu['Customer Demand'].sum()

    # Check if there are customers served by more than one warehouse
    multi_sourced = {}
    for c in customers_id:
        suppliers = sum([1 if assignment_vars[w, c].varValue > 0 else 0 for w in warehouses_id ])
        if suppliers > 1:
            multi_sourced[c] = suppliers

    if multi_sourced:
        print()
        print('Customers served by more than one warehouse')
        for k, v in multi_sourced.items():
            print(f'- Customer {k} is served by {v} warehouses')
        print()

    if plot:
        plot_map(warehouses=warehouses,
                 customers=customers,
                 flows=flows,
                 active_warehouses=active_warehouses,
                 hide_inactive=hide_inactive,
                 multi_sourced=multi_sourced,
                 **kwargs)
        # plt.figure(figsize=(fig_x, fig_y), dpi=dpi)

        # # Plot flows
        # for flow in flows:
        #     plt.plot(
        #             [warehouses[flow[0]].longitude, customers[flow[1]].longitude],
        #             [warehouses[flow[0]].latitude, customers[flow[1]].latitude],
        #             color="k",
        #             linestyle="-",
        #             linewidth=0.3)
        
        # # Plot customers
        # for c_id, each in customers.items():
        #     # Highlight customers served by multiple suppliers
        #     if c_id in multi_sourced:
        #         plt.plot(each.longitude, each.latitude, "oy", markersize=5)
        #     else:
        #         plt.plot(each.longitude, each.latitude, "ob", markersize=kwargs.get('customer_markersize', 3))
        
        # # Plot active warehouses
        # for k, each in warehouses.items():
        #     if k in active_warehouses:
        #         plt.plot(each.longitude, each.latitude, "sr", markersize=kwargs.get('warehouse_markersize', 4))

        # # Remove axes
        # plt.gca().axes.get_xaxis().set_visible(False)
        # plt.gca().axes.get_yaxis().set_visible(False)

    return {'objective_value': pl.value(pb.objective),
            'avg_weighted_distance': avg_weighted_distance,
            'active_warehouses_id': active_warehouses,
            'active_warehouses_name': [warehouses[w].name for w in active_warehouses],
            'most_distant_customer': df_cu['Distance'].max(),
            'demand_perc_by_ranges': demand_perc_by_ranges,
            'avg_customer_distance': df_cu['Distance'].mean(),
            'multi_sourced_customers': list(multi_sourced.keys())
            }

def plot_map(warehouses=None,
             customers=None,
             flows=None,
             multi_sourced=None,
             active_warehouses=None,
             hide_inactive=False,
             **kwargs):
    """ Plot the network data
        :param warehouses: list of warehouses
        :param customers: list of customers
        :param flows: plot flows between warehouses and customers
        :param active_warehouses: list of warehouses to be plotted as active
        :param hide_inactive: if true, the warehouses not in the active_warehouses list will be hidden
        :param multi_sourced: list of customers receiving flows from more than one warehouse. These will be plotted in a different color
        :param warehouse_active_marker: shape of the active warehouse icons; allowed values are s=square, o=circle, *=star, ^=triangle, v=inverted triangle
        :param warehouse_active_markercolor: color of the active warehouse icons. Allowed values are red, green, blue, black, yellow
        :param warehouse_active_markersize: size of the active warehouse icons
        :param warehouse_marker: shape of the warehouse icons; allowed values are s=square, o=circle, *=star, ^=triangle, v=inverted triangle
        :param warehouse_markercolor: color of the warehouse icons. Allowed values are red, green, blue, black, yellow
        :param warehouse_markersize: size of the warehouse icons
        :param customer_multisourced_marker: shape of the multisourced customer icons; allowed values are s=square, o=circle, *=star, ^=triangle, v=inverted triangle
        :param customer_multisourced_markercolor: color of the multisourced customer icons. Allowed values are red, green, blue, black, yellow
        :param customer_multisourced_markersize: size of the multisourced customer icons
        :param customer_marker: shape of the customer icons; allowed values are s=square, o=circle, *=star, ^=triangle, v=inverted triangle
        :param customer_markercolor: color of the customer icons. Allowed values are red, green, blue, black, yellow
        :param customer_markersize: size of the customer icons
        :return: plot of the data
     """

    if not multi_sourced:
        multi_sourced = {}

    if not active_warehouses:
        active_warehouses = []

    fig, ax = plt.subplots(figsize=(fig_x, fig_y), dpi=dpi)
    # plt.figure(figsize=(fig_x, fig_y), dpi=dpi)

    # Plot flows
    if flows:
        for flow in flows:
            plt.plot(
                    [warehouses[flow[0]].longitude, customers[flow[1]].longitude],
                    [warehouses[flow[0]].latitude, customers[flow[1]].latitude],
                    color="k",
                    linestyle="-",
                    linewidth=0.3)
    
    # Plot warehouses
    if warehouses:
        for k, each in warehouses.items():
            if k in active_warehouses:
                plt.plot(each.longitude,
                        each.latitude,
                        marker=kwargs.get('warehouse_active_marker', 'v'),
                        color=kwargs.get('warehouse_active_markercolor', 'green'),
                        markersize=kwargs.get('warehouse_active_markersize', 5))
            else:
                if not hide_inactive:
                    plt.plot(each.longitude,
                            each.latitude,
                            marker=kwargs.get('warehouse_marker', 's'),
                            color=kwargs.get('warehouse_markercolor', 'red'),
                            markersize=kwargs.get('warehouse_markersize', 4))

    # Plot customers
    if customers:
        for c_id, each in customers.items():
            # Highlight customers served by multiple suppliers
            if c_id in multi_sourced.keys():
                plt.plot(each.longitude,
                        each.latitude,
                        marker=kwargs.get('customer_multisourced_marker', '*'),
                        color=kwargs.get('customer_multisourced_markercolor', 'yellow'),
                        markersize=kwargs.get('customer_multisourced_markersize', 5))
            else:
                plt.plot(each.longitude,
                        each.latitude,
                        marker=kwargs.get('customer_marker', 'o'),
                        color=kwargs.get('customer_markercolor', 'blue'),
                        markersize=kwargs.get('customer_markersize', 4))

    # Remove axes
    plt.gca().axes.get_xaxis().set_visible(False)
    plt.gca().axes.get_yaxis().set_visible(False)
    ####################

    annot = ax.annotate("", xy=(0,0), xytext=(-20,20),textcoords="offset points",
                        bbox=dict(boxstyle="round", fc="w"),
                        arrowprops=dict(arrowstyle="->"))
    annot.set_visible(False)

    def update_annot(ind):
        x,y = line.get_data()
        annot.xy = (x[ind["ind"][0]], y[ind["ind"][0]])
        text = "{}, {}".format(" ".join(list(map(str,ind["ind"]))), 
                            " ".join([names[n] for n in ind["ind"]]))
        annot.set_text(text)
        annot.get_bbox_patch().set_alpha(0.4)


    def hover(event):
        vis = annot.get_visible()
        if event.inaxes == ax:
            cont, ind = line.contains(event)
            if cont:
                update_annot(ind)
                annot.set_visible(True)
                fig.canvas.draw_idle()
            else:
                if vis:
                    annot.set_visible(False)
                    fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", hover)

    plt.show()
    ############
