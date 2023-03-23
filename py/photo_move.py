import datetime
import exifread
import logging
import os

dir = "/mnt/Camera_Uploads"
year = "2017"

os.chdir(dir)
files = os.listdir(year)

for file in files:
  with open(f'{year}/{file}', "rb") as f:
    tags = exifread.process_file(f, details=False)
    f.close

  if  "Image DateTime" in tags.keys():
    make = str(tags["Image Make"])
    photo_time_str = str(tags["Image DateTime"])
    photo_time = datetime.datetime.strptime(photo_time_str[0:19], "%Y:%m:%d %H:%M:%S")
    photo_year = photo_time.year
    photo_month = photo_time.month

    if not os.path.exists(f'{make}/{photo_year}/{photo_month}'):
      os.makedirs(f'{make}/{photo_year}/{photo_month}')

    os.rename(f"{year}/{file}", f"{make}/{photo_year}/{photo_month}/{file}")
    print(make, photo_time, photo_year, photo_month)
