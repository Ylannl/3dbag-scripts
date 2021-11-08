import argparse
import json
import csv

from owslib.wfs import WebFeatureService
from shapely.geometry import Polygon
from shapely.strtree import STRtree

def get_all_tiles():
  wfs11 = WebFeatureService(url='https://data.3dbag.nl/api/BAG3D_v2/wfs', version='1.1.0')
  response = wfs11.getfeature(typename='BAG3D_v2:bag_tiles_3k', srsname='urn:x-ogc:def:crs:EPSG:28992', outputFormat='json')

  tiles = json.loads( response.read().decode('utf-8') )['features']

  return [ (tile['properties']['tile_id'], Polygon(tile['geometry']['coordinates'][0])) for tile in tiles ]

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument("--pattern", help="filpath pattern where cityjson files can be found", type=str, default="/data/3DBAGv2/export/cityjson/v210908_fd2cee53/3dbag_v210908_fd2cee53_{TID}.json.gz")
  parser.add_argument("output", help="name of output file", type=str)
  args = parser.parse_args()

  tiles = get_all_tiles()
  tiles_by_polyid = { id(t[1]) : t[0] for t in tiles }
  tree = STRtree( [t[1] for t in tiles] )

  tile_neighbours = {}
  for idx, geom in tiles:
    tile_neighbours[idx] = [ tiles_by_polyid[id(r)] for r in tree.query(geom) if id(r) != id(geom) ]

  with open(args.output, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile, delimiter=';')
    for tile, neighbours in tile_neighbours.items():
      writer.writerow([args.pattern.format(TID=tile)] + [args.pattern.format(TID=n) for n in neighbours])