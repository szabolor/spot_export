#!/usr/bin/python3
from __future__ import print_function, unicode_literals
import argparse
import sys
from os.path import dirname, basename, relpath, isdir, abspath, join, getctime
from os import curdir, pardir, sep, walk, makedirs
import errno
import re
import random
from PIL import Image
from PIL.ExifTags import TAGS
import json
from collections import OrderedDict
from datetime import datetime
import time
from uuid import uuid4

global SUBLIST
SUBLIST = """+++
title = "%s"
date = "%s"
type = "sublist"
levels = [
  "%s",
  "%s"
]
uuid = "%s"
events = [ ]
cover = "%s"
gallerybase = "%s"
+++
"""


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def mkdir_p(path):
  try:
    makedirs(path)
  except OSError as exc:  # Python >2.5
    if exc.errno == errno.EEXIST and isdir(path):
      pass
    else:
      raise

def generate_photo_convert_list(dir_name, file_list, out_gallery,
                                gallery_base_path, convert_log, content_params):
  websize = content_params["websize"]
  thumbsize = content_params["thumbsize"]

  out_dir = join(abspath(out_gallery), gallery_base_path)
  mkdir_p(join(out_dir, str(websize)))
  mkdir_p(join(out_dir, str(thumbsize)))

  print("Writing log...")
  with open(convert_log, "a") as log:
    for file in file_list:
      if file.endswith("jpg"):
        log.write("%s; %s; %s\n" % (join(dir_name, file), out_dir, file))


def sanitize_gallery_name(name):
  SINGLE_WORD_LIST = ["nap"]

  name = name.lower().replace('.', '')

  # try to split the album name by the first '_'
  splitted = name.split('_', 1)
  if len(splitted) == 2:
    # then there was a '_' character ;)
    # let's investigate the perix
    # maybe it's in a form of '01_albumname' or '2014.06.08_albumname'
    if re.search(r'^\d{2,}', splitted[0]):
      return splitted[1]
    # it's more dangerous to remove a single-digit prefix: '0_nap', '1_nap'...
    if splitted[0][0] in "0123456789" and splitted[1].lower() not in SINGLE_WORD_LIST:
      return splitted[1]

  # we tried, but failed
  # but it may be a valid name, return it as-is
  return name


def get_photo_data(
  dir_name,
  path,
  file_list,
  gallery_name,
  album_name,
  content_params,
  single_depth
):
  photos = []
  dates = []
  cover_candidates = []

  for file in file_list:
    if not file.endswith("jpg"):
      continue

    try:
      img = Image.open(join(dir_name, file))

      # find image dimesions resized to websize maximal side width
      websize = content_params["websize"]
      width, height = img.size
      if width > height:
        width, height = websize, websize/float(width)*height
      else:
        width, height = websize/float(height)*width, websize

      photos.append({
        "filename": file,
        "width": int(width),
        "height": int(height),
      })

      # get image capture time
      photo_date = ""

      # Try to find EXIF info about date
      # do it graciously to avid missing exif issues
      try:
        for tag, value in img._getexif().items():
          decoded = TAGS.get(tag, tag)
          if decoded.lower() in ("datetime", "datetimeoriginal"):
            photo_date = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
            # print("photo_date by EXIF datetime/datetimeoriginal")
            break
      except:
        pass

      # Try to find date by album name, like '2014.07.06_event...'    
      # print("album_name_not_sanitized: %s" % album_name_not_sanitized)
      if not photo_date:
        d = re.search(r"^(\d{4})(\d{2})(\d{2})", album_name)
        if d:
          photo_date = datetime(int(d.group(1)), int(d.group(2)), int(d.group(3)))
          # print("photo_date by album name")

      # Try to find date by gallery name, like '2014.07.06_gallerytitle...'          
      if not photo_date:
        d = re.search(r"^(\d{4})(\d{2})(\d{2})", gallery_name)
        if d:
          photo_date = datetime(int(d.group(1)), int(d.group(2)), int(d.group(3)))
          # print("photo_date by gallery name")

      # Fallback to file creation time...
      if not photo_date:
        photo_date = getctime(join(dir_name, file))
        # print("photo_date by file creation time")
      else:
        photo_date = time.mktime(photo_date.timetuple())

      # print("photo_date:", photo_date)
      dates.append(photo_date)

      # if it's a landscape photo, then it's a candidate for being cover image
      if (width > height):
        cover_candidates.append(file)

    except Exception as e:
      eprint("Error processing '%s' file" % file)
      eprint("Exception: %s" % e)

  # sample at the one-forth of the whole durration and
  # hope it'll be on the day od the event
  try:
    date = sorted(dates)[len(dates)//4]
    date = datetime.fromtimestamp(date).strftime('%Y-%m-%dT%H:%M:%SZ')
  except Exception as e:
    eprint("Exception at date calculation: %s" % e)
    date = "2000-01-01"
  print("Final date: %s" % date)
  
  print("")
  if single_depth:
    content_filename = gallery_name.lower()
    title = sanitize_gallery_name(content_filename)
  else:
    content_filename = join(gallery_name, path)
    title = sanitize_gallery_name(album_name)
  title = title.replace('_', ' ')

  try:
    cover_photo = random.choice(cover_candidates)
    cover_photo = join(str(content_params["thumbsize"]), cover_photo)
  except:
    cover_photo = "NONE"

  # Sort photos by filenames
  # TODO: sort by date AND after filename
  photos = sorted(photos, key=lambda k: k['filename'])

  return {
    "photos": photos,
    "cover_photo": cover_photo,
    "title": title,
    "date": date,
    "content_filename": content_filename,
  }


def structure_sublist_to_content(
  content_base_path,
  gallery_name,
  path,
  struct
):
  if not path or path == curdir:
    content_file_path = join(content_base_path, gallery_name + ".md")
  else:
    print(join(content_base_path, gallery_name, path))
    mkdir_p(join(content_base_path, gallery_name, path))
    content_file_path = join(content_base_path, gallery_name, path + ".md")
  
  print("Writing [sublist] content to %s" % content_file_path)
  with open(content_file_path, "w") as f:
    f.write(SUBLIST % (
        sanitize_gallery_name(struct["title"]).replace('_', ' '),
        struct["date"],
        struct["parent"],
        struct["uuid"],
        struct["uuid"],
        struct["cover"],
        struct["gallerybase"]
      )
    )

def structure_photo_to_content(
  content_base_path,
  content_params,
  structure_photo,
  photo_data
):
  #print(photo_data)
  post = OrderedDict([
    ('title', photo_data["title"]),
    ('date', photo_data["date"]),
    ('gallerybase', join(
      content_params["gallery_base_url"],
      photo_data["content_filename"])),
    ('cover', photo_data["cover_photo"]),
    ('levels', [ structure_photo["parent"], structure_photo["uuid"] ]),
    ('uuid', structure_photo["uuid"]),
    ('thumbprefix', content_params["thumbsize"]),
    ('webprefix', content_params["websize"]),
    ('photos', photo_data["photos"]),
  ])
  content_file_path_wo_ext = join(content_base_path, photo_data["content_filename"])
  print("Writing [photo] content to %s" % content_file_path_wo_ext)
  mkdir_p(join(content_base_path, dirname(photo_data["content_filename"])))
  with open(content_file_path_wo_ext + ".md", "w") as f:
    f.write(json.dumps(post, indent=2, separators=(',', ': ')))


def structure_to_content(
  content_base_path,
  content_params,
  structure
):
  gallery_name = structure[curdir]["title"]

  if len(structure) == 1:
    mkdir_p(content_base_path)
    photo_data = get_photo_data(
      dir_name=structure[curdir]["dir_name"],
      path="",
      file_list=structure[curdir]["file_list"],
      gallery_name=gallery_name,
      album_name=structure[curdir]["title"],
      content_params=content_params,
      single_depth=True
    )
    structure_photo_to_content(
      content_base_path=content_base_path,
      content_params=content_params,
      structure_photo=structure[curdir],
      photo_data=photo_data
    )
  else:
    mkdir_p(join(content_base_path, gallery_name))

    # evaluate photo params (date, cover)
    for path, struct in structure.items():
      if struct["type"] == "photo":
        #print("Sanitized_PATH: %s" % struct["path"])
        photo_data = get_photo_data(
          dir_name=struct["dir_name"],
          path=struct["path"],
          file_list=struct["file_list"],
          gallery_name=gallery_name,
          album_name=struct["title"],
          content_params=content_params,
          single_depth=False
        )

        structure[path]["date"] = photo_data["date"]
        structure[path]["title"] = photo_data["title"]
        structure[path]["cover"] = photo_data["cover_photo"]
        structure[path]["gallerybase"] = join(
          content_params["gallery_base_url"],
          photo_data["content_filename"]
        )

        structure_photo_to_content(
          content_base_path=content_base_path,
          content_params=content_params,
          structure_photo=struct,
          photo_data=photo_data
        )

    # inherit params to sublist parents
    # use sorted array which sort the shorter prefixes to the beginning
    for path in sorted(structure.keys(), reverse=True):
      parent = dirname(path)
      if not parent:
        parent = curdir
      if parent in structure and structure[parent]["type"] == "sublist":
        structure[parent]["date"] = structure[path]["date"]
        structure[parent]["cover"] = structure[path]["cover"]
        structure[parent]["gallerybase"] = structure[path]["gallerybase"]

    for path, struct in sorted(structure.items()):
      if struct["type"] == "sublist":
        print("SUBDIR_path: %s" % struct["path"])
        structure_sublist_to_content(
          content_base_path=content_base_path,
          gallery_name=gallery_name,
          path=struct["path"],
          struct=struct
        )


def export_web(in_gallery, out_gallery, content_path, convert_log, 
               gallery_base_url, websize, thumbsize):
  WEB_FOLDER = "web"
  DONTCARE_FOLDERS_BY_NAME = ["tmp"]
  DONTCARE_FOLDERS_BY_WORD = ["lofasz"]
  
  content_params = {
    "gallery_base_url": gallery_base_url,
    "websize": websize,
    "thumbsize": thumbsize,
  }

  # stripping trailing '/', because of basename
  in_gallery = in_gallery.rstrip(sep)
  out_gallery = out_gallery.rstrip(sep)
  content_path = content_path.rstrip(sep)

  # get the album name, convert to lowercase and remove every dot 
  # (hugo don't like it)
  gallery_name = basename(in_gallery).lower().replace('.', '')

  print("Gallery name: %s" % gallery_name)
  
  print("Searching for 'web' directories...")

  uuid_store = {}
  structure = {}

  # python will use to-down folder walking
  for dir_name, subdir_list, file_list in walk(in_gallery):
    dir_basename = basename(dir_name)
    dir_relpath = relpath(dir_name, in_gallery)
    #print("dir_basename: %s" % dir_basename)
    #print("dir_relpath: %s" % dir_relpath)
    uuid_store[dir_relpath] = str(uuid4())

    #print(uuid_store)

    # found a web folder!
    if dir_basename == WEB_FOLDER:
      album_rel = dirname(dir_relpath)
      album_rel_parent = dirname(album_rel)
      #print(" > album_rel: %s" % album_rel)

      # the found 'web' folder's relative path to the input base path
      print("Found '%s' directory in '%s' folder with %d files" % 
           (WEB_FOLDER, album_rel, len(file_list)))

      # check for any trace of an invalid album (e.g. 'tmp', 'lofasz', etc...)
      if dir_basename in DONTCARE_FOLDERS_BY_NAME:
        eprint("The relative path is seems to be a DONTCARE folder name!")
        eprint(" >> SKIPPING folder [%s]" % album_rel)
        continue
      if any(map(lambda word: word in dir_basename, DONTCARE_FOLDERS_BY_WORD)):
        eprint("Found a DONTCARE word in the relative path")
        eprint(" >> SKIPPING folder [%s]" % album_rel)
        continue

      if not album_rel:
        # it's a single-depth gallery
        structure[curdir] = {
          "type": "photo",
          "title": gallery_name,
          "dir_name": dir_name,
          "file_list": file_list,
          "uuid": uuid_store[dir_relpath],
          "parent": uuid_store[dir_relpath],
        }
      else:
        if curdir not in structure:
          structure[curdir] = {
            "type": "sublist",
            "path": "",
            "title": gallery_name,
            "uuid": uuid_store[curdir],
            "parent": uuid_store[curdir],
          }
        # add album parents to the to-be-exported list
        accumulate_path = ""
        accumulate_sanitized_path = ""
        print("album_rel: '%s'" % album_rel)

        for parent_dir in album_rel.split(sep)[:-1]:
          print("parent_dir: '%s'" % parent_dir)

          next_accumulate_path = join(accumulate_path, parent_dir)
          next_accumulate_sanitized_path = join(
            accumulate_sanitized_path,
            sanitize_gallery_name(parent_dir)
          )

          if next_accumulate_path not in structure:
            structure[next_accumulate_path] = {
              "type": "sublist",
              "path": next_accumulate_sanitized_path,
              "title": parent_dir,
              "uuid": uuid_store[next_accumulate_path],
              "parent": uuid_store[accumulate_path if accumulate_path else curdir],
            }
          print("next_accumulate_sanitized_path: '%s'" % next_accumulate_sanitized_path)
          accumulate_path = next_accumulate_path
          accumulate_sanitized_path = next_accumulate_sanitized_path

        # add gallery itself
        structure[album_rel] = {
          "type": "photo",
          "title": basename(album_rel),
          "path": sep.join(
            map(lambda p: sanitize_gallery_name(p), album_rel.split(sep))
          ),
          "dir_name": dir_name,
          "file_list": file_list,
          "uuid": uuid_store[dir_relpath],
          "parent": uuid_store[album_rel_parent if album_rel_parent else curdir],
        }

  # END os.walk

  structure_to_content(
    content_base_path=content_path,
    content_params=content_params,
    structure=structure
  )

  #print("returned gallery_base_path: %s" % gallery_base_path)

  # generate conversion lists
  # generate_photo_convert_list(
  #   dir_name, file_list, out_gallery, gallery_base_path, convert_log, content_params
  # )

      

  print("end...")


if __name__ == '__main__':
  parser = argparse.ArgumentParser(
    description='SPOT album converter for Web and Signage (aka Plazma) usage'
  )
  parser.add_argument('-v', '--verbose', action='count', default=0,
                    help='increase output verbosity')
  parser.add_argument('-i', "--input", action='store', dest='input_path',
                    help='base path of the input (to-be-converted) gallery')
  parser.add_argument('-o', "--output", action='store', dest='output_path',
                    help='base path of the converted gallery')
  parser.add_argument('-c', "--content", action='store', dest='content_path',
                    help='base path for the converted gallery content file')
  parser.add_argument('-g', "--gallerybase", action='store', dest='gallery_base_path',
                    help='base URL/folder for web gallery images')
  parser.add_argument('-w', "--websize", action='store', dest='web_max_size',
                    help='maximal side size of the web converted image',
                    type=int, default=2048)
  parser.add_argument('-t', "--thumbsize", action='store', dest='thumb_max_height_size',
                    help='maximal height(!) size of the web converted image',
                    type=int, default=400)
  parser.add_argument('-n', "--title", action='store', dest='gallery_title',
                    help='human readable gallery title (only for the top-level gallery!)',
                    type=int, default=400)
  parser.add_argument('-l', "--convert", action='store', dest='convert_log',
                help='file output for file-list log used for converting/copying images')
  args = parser.parse_args()

  print("Exporting with the following setup:")
  print("  INPUT_PATH:            %s" % args.input_path)
  print("  OUTPUT_PATH:           %s" % args.output_path)
  print("  CONTENT_PATH:          %s" % args.content_path)
  print("  GALLERY_BASE_PATH:     %s" % args.gallery_base_path)
  print("  CONVERT_LOG:           %s" % args.convert_log)
  print("  WEB_MAX_SIZE:          %d" % args.web_max_size)
  print("  THUMB_MAX_HEIGHT_SIZE: %d" % args.thumb_max_height_size)
  print("-----------------------------------")


  # check for required options:
  if any(map(lambda x: not x, [args.input_path, args.output_path, args.content_path,
                               args.gallery_base_path, args.convert_log])):
    eprint("At least one of the required options are missing, please check it!")
    sys.exit(1)

  # delete log file content
  with open(args.convert_log, "w") as f:
    pass

  export_web(
    args.input_path, 
    args.output_path,
    args.content_path,
    args.convert_log,
    args.gallery_base_path,
    args.web_max_size,
    args.thumb_max_height_size
  )
