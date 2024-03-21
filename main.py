import argparse
import datetime
import sys

import folium
from folium.plugins import LocateControl, MeasureControl
from pyhafas import HafasClient
from pyhafas.profile import DBProfile
from pyhafas.types.fptf import Station

# Create a HafasClient object with the DBProfile
hafas_client = HafasClient(DBProfile())

def convert_station_str_to_station(station_str: str) -> Station:
    
    # Get the locations for the station string from the HAFAS API
    locations = hafas_client.locations(station_str)
    station = None

    # If no locations are found, print an error message and exit
    if len(locations) == 0:
        print(f"Could not find any stations with the name {station_str}")
        sys.exit(1)
    # If only one location is found, use that location
    if len(locations) == 1:
        print(f"Found the following station: {locations[0]}")
        station = locations[0]
    # If multiple locations are found, print the top 5 locations and ask the user to select one
    else:
        print(f"Found the following stations:")
        for i, location in enumerate(locations[:5]):
            print(f"{i+1}: {location.name}")
        try:
            start_station_index = int(input("Please select the station you want to use: "))-1
            station = locations[start_station_index]
        except ValueError:
            print("Invalid input")
            sys.exit(1)
        except IndexError:
            print("Invalid index")
            sys.exit(1)
    return station

    
            
    
def draw(journey,only_transfer_stations=False):
    # Create a map with the location of the origin station as the center
    origin_lat, origin_lon = journey.legs[0].origin.latitude, journey.legs[0].origin.longitude
    map = folium.Map(location= [origin_lat, origin_lon],zoom_start=8)
    
    # Add the locate and measure controls to the map
    LocateControl().add_to(map)
    MeasureControl().add_to(map)
    


    # initialize the transfer count for the color of the lines
    transfer_count = 0
    # Iterate over the legs of the journey
    for leg in journey.legs:
        # Create a list of points for the polyline of this leg
        route_line_points = []
        # If only_transfer_stations is False, add all stopovers to the route_line_points list
        if only_transfer_stations == False:
            for stopover in leg.stopovers:
                stop = stopover.stop
                # Add the location of the stopover to the route_line_points list for the polyline
                route_line_points.append((stop.latitude,stop.longitude))
                # Add a circle marker for the stopover to the map
                folium.Circle(
                    radius=1000,
                    location=[stop.latitude,stop.longitude],
                    popup=f"{stop.name} - {stopover.departure.strftime('%H:%M %d.%m.%Y') if stopover.departure is not None else stopover.arrival.strftime('%H:%M %d.%m.%Y') if stopover.arrival is not None else 'unknown'}",
                    color="crimson",
                    fill=True,
                ).add_to(map)
        else: 
            # If only_transfer_stations is True, only add the origin and destination of the leg to the route_line_points list
            route_line_points.append((leg.origin.latitude,leg.origin.longitude))
            folium.Circle(
                radius=1000,
                location=[leg.origin.latitude,leg.origin.longitude],
                popup=f"{leg.origin.name} - {leg.departure.strftime('%H:%M %d.%m.%Y')}",
                color="crimson",
                fill=True,
            ).add_to(map)
            route_line_points.append((leg.destination.latitude,leg.destination.longitude))
            folium.Circle(
                radius=1000,
                location=[leg.destination.latitude,leg.destination.longitude],
                popup=f"{leg.destination.name} - {leg.arrival.strftime('%H:%M %d.%m.%Y')}",
                color="crimson",
                fill=True,
            ).add_to(map)
        # Add the polyline for the leg to the map
        folium.PolyLine(route_line_points,color=["Red","Blue","Green","Black","White"][transfer_count%5]).add_to(map)
        transfer_count += 1
    
    return map

def draw_and_save_to_file(train_journey,only_transfer_stations=False, map_filename="output.html"):
    """Draws a map of a train journey and saves it to a file.

    Args:
        train_journey (pyhafas.types.fptf.Journey): The train journey to draw.
        only_transfer_stations (bool, optional): If True, only the transfer stations are drawn. Defaults to False.
        map_filename (str, optional): The filename to save the map to. Defaults to "output.html".
    """
    # Draw the map and save it to a file
    map = draw(train_journey,only_transfer_stations)
    map.save(map_filename)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape a journey from the DB API and convert it to JSON")
    parser.add_argument("-s", "--start",help="The name of the start station", type=str, dest="start_station_str")
    parser.add_argument("-d", "--destination",help="The name of the destination station", type=str, dest="destination_station_str")
    parser.add_argument("-t", "--start-time",help="The start time of the journey in the format YYYY-MM-DDTHH:MM", required=False, type=lambda s: datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M"), dest="start_time")
    args = parser.parse_args()



    # if args.start_time is None use the current time
    if args.start_time is None:
        print("No start time specified. Do you want to use the current time?")
        use_current_time = input("y/n: ")
        if use_current_time.lower() == "y":
            args.start_time = datetime.datetime.now()
        else:
            args.start_time = input("Please enter the start time in the format YYYY-MM-DDTHH:MM: ")
            try:
                args.start_time = datetime.datetime.strptime(args.start_time, "%Y-%m-%dT%H:%M")
            except ValueError:
                print("Invalid time format")
                sys.exit(1)
    # If the start or destination station strings are not specified, ask the user to input them
    if args.start_station_str is None:
        args.start_station_str = input("Please enter the name of the start station: ")
    if args.destination_station_str is None:
        args.destination_station_str = input("Please enter the name of the destination station: ")

    # Get the stations for the start and destination station strings and generate the journey
    start_station =  convert_station_str_to_station(args.start_station_str)
    destination_station = convert_station_str_to_station(args.destination_station_str)
    journeys = hafas_client.journeys(
        origin=start_station,
        destination=destination_station,
        date=args.start_time
    )

    # Print the possible routes and ask the user to select one
    print(f"Found {len(journeys)} possible routes for your trip from {start_station.name} to {destination_station.name} at {args.start_time}")
    for i,journey in enumerate(journeys):
        if len(journey.legs) == 1:
            print(f"- {i}: Journey starts at {journey.legs[0].departure.strftime('%H:%M %d.%m.%Y')} and ends at {journey.legs[-1].arrival.strftime('%H:%M %d.%m.%Y')}. The complete journey takes {journey.duration} and has no changes")
        else:
            print(f"- {i}: Journey starts at {journey.legs[0].departure.strftime('%H:%M %d.%m.%Y')} and ends at {journey.legs[-1].arrival.strftime('%H:%M %d.%m.%Y')}. The complete journey takes {journey.duration} and has {len(journey.legs)-1} changes (at {', '.join([leg.destination.name for leg in journey.legs[:-1]])})")
    route_selection = int(input("Please select the journey you want to use: "))
    # If the user input is invalid, print an error message and exit
    if route_selection < 0 or route_selection >= len(journeys):
        print("Invalid selection")
        sys.exit(1)

    # Save the selected route to a file
    draw_and_save_to_file(journeys[route_selection], False)
    print(f"Saved map")





    
    

