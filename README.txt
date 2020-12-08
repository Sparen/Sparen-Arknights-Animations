Part 1 - Obtaining Animations
1. Visit https://arknights.nuke.moe
2. Select the character and animation. Use the green background since it's easy to use for removal, or Red/Blue based on what colors are in use on the character's sprites (They don't support transparent export yet)
3. Hit record and record the duration of the animation (two loops is best)
4. Hit output after waiting a bit. Note that the output window doesn't refresh, so close it and reopen to see if it's done processing
5. Download GIF

Part 2 - GIF Processing
1. Determine the start and end frames of the animation
2. Use gifsicle (https://www.lcdf.org/gifsicle/, install w/ Homebrew) to crop to the specified frames
   Note: End is inclusive, so #0-10 will produce 11 frames.
   Format: gifsicle input.gif "#start-end" -o output.gif
   Example: gifsicle Unknown.gif "#47-123" -o output-1.gif
3. Crop the physical gif. Image is 712x512; can use LTRB of 164 112 548 496 to isolate the sprite (384x384)
   Note: 256x256 isn't large enough to contain animations, which is why we go for 384x384
   gifsicle --crop 164,112+384x384 output-1.gif -o output-2.gif

Part 3 - GIF to PNG Spritesheet
- I wrote a script to do this. It takes a GIF (with a background color) and a channel corresponding to the background color ([0 1 2] corresponding to [Red Green Blue]). There's also a thresholding parameter. Raise it to remove background artifacts.
- Note that the higher the threshold, the more likely it is that false positives will be corrected. Be careful!
  python3 colorcorrectandspritify.py output-2.gif output-f.png 1 128
