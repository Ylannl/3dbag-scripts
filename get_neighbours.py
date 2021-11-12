import argparse
import json
import csv
from pathlib import Path

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
  parser.add_argument("--pattern", help="filpath pattern where cityjson files can be found", type=str, default="/data/3DBAGv2/export/cityjson/v210908_fd2cee53/3dbag_v210908_fd2cee53_{TID}.json")
  parser.add_argument("output", help="name of output file. Each line has 1st the center tile and then all its neighbours.", type=str)
  args = parser.parse_args()

  tiles = get_all_tiles()
  tiles_by_polyid = { id(t[1]) : t[0] for t in tiles }
  tree = STRtree( [t[1] for t in tiles] )

  tile_neighbours = {}
  for idx, geom in tiles:
    tile_neighbours[idx] = [ tiles_by_polyid[id(r)] for r in tree.query(geom) if id(r) != id(geom) and Path(args.pattern.format(TID=tiles_by_polyid[id(r)])).exists() ]

  with open(args.output, 'w') as csvfile:
    for tile, neighbours in tile_neighbours.items():
      command = "/home/rypeters/git/urban-morphology-3d/venv/bin/python /home/rypeters/git/urban-morphology-3d/cityStats.py -dsn \"dbname=baseregisters\" -b -o {TID}_lod2_surface_areas.csv -- ".format(TID=tile)
      csvfile.write(command + " " + args.pattern.format(TID=tile) + " " + " ".join([args.pattern.format(TID=n) for n in neighbours]) + "\n")
