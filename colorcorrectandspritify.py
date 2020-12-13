#!/usr/bin/env python3

# GIF Background to Transparency utility by Andrew Fan
# Thrown together on Dec 5, 2020
# Given a GIF image with n frames and a background color that is solid red, green, or blue, converts the GIF to a PNG spritesheet with transparency
# Mode 1 (Default): Boundary2N (B2N) - Identify all pixels in pixel-based threshold, then apply processing on all pixels in the 5x5 area surrounding them. Threshold is an integer.
# Mode 2: IntensityMatrix (IM) - For the 5x5 area, uses the distance to the nearest boundary pixel for scaling rather than weighting them all equally. Initially considered ignoring the four corners to make it more circular but that doesn't get into corners well
# Thresholding parameter allows a leakier mask (e.g. if threshold is 10, [3, 254, 2] would be treated the same as [0, 255, 0]. Threshold applied as a total across all three)
# Threshold allows areas surrounding the background color tightly to be captured

# Usage:
# colorcorrectandspritify.py <input filename (GIF)> <output filename (PNG)> <channel to use, with 0 being red, 1 being green, and 2 being blue> <thresholding parameter (int, 0-255*3 scale)> <mode (optional, B2N or IM)

import sys
import shutil
import math
import numpy as np
from PIL import Image # https://pillow.readthedocs.io/en/stable/reference/Image.html
from PIL import GifImagePlugin # Necessary for n_frames to be recognized. https://pillow.readthedocs.io/en/stable/_modules/PIL/GifImagePlugin.html

inputpath = sys.argv[1]
outputpath = sys.argv[2]
channel = int(sys.argv[3])
threshold = float(sys.argv[4])
mode = "B2N"
if len(sys.argv) > 5:
	mode = sys.argv[5]

# Load input
inimg = Image.open(inputpath)
width, height = inimg.size

# Given a palette color, retrieves the RGB as an array
def get_rgb_pixel(paletteid):
	palette = inimg.getpalette() # Needs to be re-acquired for each frame since it's different for each frame
	return palette[paletteid*3:paletteid*3+3]

# Given an RGB value, determines if it is within a threshold of the mask
def is_within_threshold(pixeltuple):
	mask = [0, 0, 0]
	mask[channel] = 255 # Mark the channel that we will make transparent
	# Calculate absolute difference
	absdiff = abs(pixeltuple[0] - mask[0]) + abs(pixeltuple[1] - mask[1]) + abs(pixeltuple[2] - mask[2])
	if absdiff <= threshold:
		return True
	return False

# True if one of the neighbors matches the mask (represented by 2), False otherwise
# Using a 5x5 square to catch particularly nasty bits
# Warning: height, and width are accessed as global variables. DO NOT MUTATE
# Note: We pass a partially filled-out mask matrix. We ONLY need to check against if it has a 2 in the slot we're observing
# This program is designed for square sprites and we do square operations so hopefully this function will work regardless
def neighbor_matches_mask(x, y, matrix):
	closestdist = 10000 # Distance to closest neighbor matching the mask. Using an arbitrary large number to start
	for dx in range(x - 2, x + 3):
		if dx < 0 or dx > width:
			pass
		else:
			for dy in range(y - 2, y + 3):
				if dy < 0 or dy > height:
					pass
				else:
					if matrix[dx][dy] == 2:
						currdist = math.sqrt((dx-x)**2 + (dy-y)**2)
						if currdist < closestdist:
							closestdist = currdist
	if closestdist < 10000: # Match found
		return closestdist
	return -1

# Given a boundary pixel, adjusts the value for the channel being used for transparency. 
# Using a shitty algorithm: 
# 1. For the channel, find the deviation between the value and the average value of the other channels
# 2. Adjust the channel by the difference (IE set it to the average) and alpha by the difference, using the intensity value in IM mode
# e.g. (0, 255, 0, 255) (Green) becomes (0, 0, 0, 0)
# e.g. (0, 240, 0, 255) (Green) becomes (0, 0, 0, 15)
# e.g. (128, 128, 128, 255) (Green) stays the same
# e.g. (128, 192, 128, 255) (Green) becomes (128, 128, 128, 191)
# This is OBVIOUSLY not going to restore the original alpha value, and abuses the 1px black border around sprites
# Thin details are going to suffer greatly as far as alpha goes as well
# Warning: inimg is accessed as a global variable. DO NOT MUTATE
def process_boundary_pixel(outimg, x, y, destoffsetx, destoffsety, intensity):
	intensityscale = 1
	if mode == "IM":
		intensityscale = intensity**2 # Use the square to dissipate faster

	currpixel = get_rgb_pixel(inimg.getpixel((x, y)))
	avgvalue = (currpixel[0] + currpixel[1] + currpixel[2] - currpixel[channel])/2.0
	difference = currpixel[channel] - avgvalue
	newpixel = currpixel
	newpixel[channel] = int(currpixel[channel] - difference/intensityscale)
	outimg.putpixel((destoffsetx + x, destoffsety + y), (newpixel[0], newpixel[1], newpixel[2], 255 - int(difference/intensityscale)))

# Primary logic goes here. Generates spritesheet and processes frames of input GIF
def process_image():
	# Determine spritesheet size
	# ssdims specifies the max number of sprites per row/column
	numsprites = inimg.n_frames
	thresholdarr = [0, 1, 4, 9, 16, 25, 36, 49, 64, 81, 100, 121, 144, 169, 196, 225, 256] # If there are more than 256 frames, we've got a problem XD
	ssdims = 16 # Force a max of 16x16
	for i in range(len(thresholdarr)):
		if numsprites < thresholdarr[i]:
			ssdims = i
			break # Found the earliest one. Done.

	print ("Identified " + str(numsprites) + " frames in GIF. Generating " + str(ssdims) + "x" + str(ssdims) + " spritesheet")

	outimg = Image.new("RGBA", (ssdims * width, ssdims * height), (0, 0, 0, 0)) # Initialize to transparent

	# Operate over the frames of the copy. We go pixel by pixel within each frame so this can be SUPER slow
	for i in range(inimg.n_frames):
		print ("Processing Frame #" + str(i))
		# Define our destination pixel offsets based off of the current frame
		# We will add these whenever running putpixel on our destination image
		destoffsetx = i%ssdims * width
		destoffsety = i//ssdims * height

		inimg.seek(i)
		# Construct a 0-1-2 matrix detailing what operations to perform
		matrix = np.zeros(inimg.size) # wxh
		# Construct intensity matrix (note that handling depends on which mode we're using)
		intensitymatrix = np.zeros(inimg.size) # wxh

		# By default, matrix has 0s. We will mark pixels with 2 if they match the mask or are within a threshold
		for y in range(width):
			for x in range(height):
				if is_within_threshold(get_rgb_pixel(inimg.getpixel((x, y)))):
					matrix[x][y] = 2
		# Check for adjacent pixels
		for y in range(width):
			for x in range(height):
				# To do this check efficiently, we pass the partially generated matrix, which has been prefilled with 2s
				# We're mutating it live, but that doesn't matter since the neighbor_matches_mask() only checks against 2s
				if matrix[x][y] == 0:
					maskparam = neighbor_matches_mask(x, y, matrix)
					if maskparam != -1: # It is near a boundary pixel
						matrix[x][y] = 1
						intensitymatrix[x][y] = maskparam # update intensity matrix value
		# Apply changes to the OUTPUT spritesheet
		# Note that we do not write transparent pixels because they are transparent when the output image is created
		for y in range(width):
			for x in range(height):
				if matrix[x][y] == 1: # Adjust the specific channel
					process_boundary_pixel(outimg, x, y, destoffsetx, destoffsety, intensitymatrix[x][y])
				elif matrix[x][y] == 0: # Paste the existing data
					currpixel = get_rgb_pixel(inimg.getpixel((x, y)))
					outimg.putpixel((destoffsetx + x, destoffsety + y), (currpixel[0], currpixel[1], currpixel[2]))

	# Push changes
	outimg.save(outputpath)

# Run the main function
process_image()

