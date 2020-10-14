import os
import gdal
from pathlib import Path
import sys


def run():
    # in_path = '/home/harish/Downloads/crop/'
    # input_filename = 'SKI_20_clipped.tif'
    if len(sys.argv) < 6:
        print("python manage.py runscript split_tif cropped_image.tif webclient/static/dataset limit_value")
        return

    file_extension = '.png'

    input_filename = sys.argv[3]

    # out_path = '/home/harish/Downloads/images/'
    out_path = sys.argv[4]
    output_filename = 'tile_'

    Path(out_path).mkdir(parents=True, exist_ok=True)

    tile_size_x = 750
    tile_size_y = 750

    # ds = gdal.Open(in_path + input_filename)
    ds = gdal.Open(input_filename)
    band = ds.GetRasterBand(1)


    xsize = band.XSize
    ysize = band.YSize

    merge_x = 0
    merge_y = 0

    x_inc = tile_size_x
    y_inc = tile_size_y

    print("\n\nSplitting-------------------------------------------------------------------------------\n\n")
    count = 0
    count_limit = int(sys.argv[5])

    for i in range(0, xsize, tile_size_x):

        x_inc = tile_size_x
        # handle corner case
        if (i + tile_size_x > xsize):
            i = xsize - tile_size_x

        merge_y = 0
        for j in range(0, ysize, tile_size_y):

            y_inc = tile_size_y

            # handle corner case
            if (j + tile_size_y > ysize):
                j = ysize - tile_size_y

            com_string = "gdal_translate -of PNG -srcwin " + str(i) + ", " + str(j) + ", " + str(x_inc) + ", " + str(
                y_inc) + " " + str(input_filename) + " " + str(out_path) + str(output_filename) + str(
                i) + "_" + str(j) + file_extension
            os.system(com_string)
            count += 1
            print("Tile : ", i, ",", j)
            if count == count_limit:
                break
            merge_y = merge_y + tile_size_y
        merge_x = merge_x + tile_size_x
        if count == count_limit:
            break

    com_string = "rm -rf " + out_path + "*.xml"
    os.system(com_string)
    print("\n\nImage Tiling complete-------------------------------------------------------------------\n\n")
