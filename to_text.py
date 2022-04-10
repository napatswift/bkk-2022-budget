import cv2 as cv
import pytesseract
from tqdm import tqdm
import path
import pandas as pd
import sys
from os import listdir

pytesseract.pytesseract.tesseract_cmd = '/usr/local/Cellar/tesseract/5.1.0/bin/tesseract'


def matToText(filename, write=False):
    mat = cv.imread(filename)
    draw_mat = mat.copy()
    gray = cv.cvtColor(mat, cv.COLOR_BGR2GRAY)
    th, threshed = cv.threshold(
        gray, 70, 255, cv.THRESH_BINARY_INV | cv.THRESH_OTSU)
    kernel = cv.getStructuringElement(cv.MORPH_RECT, (5, 5))
    threshed = cv.dilate(threshed, kernel)
    hist = cv.reduce(threshed, 1, cv.REDUCE_AVG).reshape(-1)

    kernel = cv.getStructuringElement(cv.MORPH_RECT, (10, 5))
    dilated = cv.dilate(threshed, kernel)
    contours, _ = cv.findContours(
        dilated, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)
    rects = [cv.boundingRect(c) for c in contours]
    rects.sort(key=lambda rect: rect[1])

    h, w = mat.shape[:2]
    stack_y = []
    for ii in range(h-1):
        if (hist[ii] and not hist[ii+1]):
            stack_y.append(ii)
        elif (not hist[ii] and hist[ii+1]):
            stack_y.append(ii)

    ocr_text = []
    while(stack_y):
        y1 = stack_y.pop()
        y2 = stack_y.pop()
        line = []
        while rects:
            rect = rects[-1]
            midPoint = rect[1] + rect[3]//2
            if (y2 <= midPoint <= y1):
                cv.rectangle(
                    draw_mat, (rect[0], rect[1]), (rect[0]+rect[2], rect[1]+rect[3]), (0, 0, 255))
                line.append(rects.pop())
            else:
                break
        line.sort(key=lambda rect: rect[0]+rect[2]/2)
        ocr_text.append(
            [
                {
                    'text': pytesseract.image_to_string(mat[y:y+h, x:x+w], lang='tha+eng'),
                    'x': x,
                    'y':y,
                    'w':w,
                    'h':h,
                    'filename': filename.name
                }
                for x, y, w, h in line
            ]
        )

    if (write):
        filename = filename[filename.rfind('/')+1:filename.rfind('.')]
        cv.imwrite(f"{filename}drawed.jpg", draw_mat)
        cv.imwrite(f"{filename}dilated.jpg", dilated)
        cv.imwrite(f"{filename}threshed.jpg", threshed)

    return ocr_text


def writeImages(df, src_dir, dest_dir):
    currImageFilename = df.loc[0].filename
    currImage = cv.imread(src_dir + '/' + currImageFilename)
    for row in df.iterrows():
        if currImageFilename != row[1].filename:
            cv.imwrite(dest_dir + '/' + currImageFilename, currImage)
            currImageFilename = row[1].filename
            currImage = cv.imread(src_dir + '/' + currImageFilename)
        cv.rectangle(currImage, (row[1].x, row[1].y),
                     (row[1].x+row[1].w, row[1].y+row[1].h), (0, 0, 255))
        cv.putText(currImage, f"{row[1].x}, {row[1].y}",
                   (row[1].x, row[1].y), 0, .5, (0, 0, 255))
    cv.imwrite(dest_dir + '/' + currImageFilename, currImage)

def main():
    dir = path.Path(sys.argv[1])

    pages = listdir(dir)
    pages.sort()

    text_list = []
    for ii in tqdm(pages):
        filepath = path.Path(dir + '/' + ii)
        text = matToText(filepath)
        text_list.append(text)

    df_text = []
    for page in text_list:
        line_num = 0
        for line in page[::-1]:
            for block in line:
                block['text'] = block['text'].replace('\n', '')
                block['line_num'] = line_num
                df_text.append(block)
            line_num += 1

    df = pd.DataFrame(df_text)

    csv_dir = path.Path('bud-csv')
    if not csv_dir.exists():
      csv_dir.mkdir();

    df.to_csv(f"{csv_dir}/{dir.basename()}_raw.csv", index=0)

    rects_dir = path.Path(dir+'/'+'rects')
    if not rects_dir.exists():
      rects_dir.mkdir();

    writeImages(df, dir, rects_dir)

if __name__ == "__main__":
  main()