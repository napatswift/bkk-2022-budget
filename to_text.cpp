#include <string>
#include <tesseract/baseapi.h>
#include <leptonica/allheaders.h>
#include <opencv2/opencv.hpp>
#include <filesystem>
#include <fstream>

using namespace cv;

std::string splitFileName(std::string filepath)
{
    size_t start = filepath.rfind('/');
    size_t end = filepath.rfind('.');
    return filepath.substr(start + 1, end - start - 1);
}

std::vector<std::vector<Rect>> lineBlock(Mat src)
{
    std::vector<std::vector<Rect>> lineBounds;

    if (src.empty())
    {
        std::cerr << "[error]: image is empty" << std::endl;
        return lineBounds;
    }

    Mat dest;

    cvtColor(src, src, COLOR_BGR2GRAY);
    src.copyTo(dest);
    src = src < 200;

    Mat kernel = getStructuringElement(MORPH_RECT, Size(1, 5));
    dilate(src, src, kernel);

    Mat1f horProj;
    reduce(src, horProj, 1, REDUCE_AVG);
    Mat1b hist = horProj <= 0;

    kernel = getStructuringElement(MORPH_RECT, Size(13, 2));
    dilate(src, src, kernel);
    std::vector<std::vector<Point>> contours;
    findContours(src, contours, RETR_EXTERNAL, CHAIN_APPROX_NONE);

    std::vector<Rect> rects;
    for (std::vector<Point> contour : contours)
    {
        Rect rect = boundingRect(contour);
        rects.push_back(rect);
    }

    int prevR = -1;
    bool isSpace = true;
    size_t lineNumber = 0;
    for (size_t r = 0; r < src.rows; r++)
    {
        if (isSpace)
        {
            if (!hist(r))
            {
                isSpace = false;
                prevR = r;
            }
        }
        else
        {
            if (hist(r))
            {
                isSpace = true;
                std::vector<Rect> line;
                do
                {
                    Rect rect = rects.back();
                    double mid = rect.y + rect.height / 2;

                    if (!(mid < r && mid > prevR))
                    {
                        break;
                    }

                    line.push_back(rect);
                    rects.pop_back();
                } while (!rects.empty());

                lineBounds.push_back(line);
            }
        }
    }
    return lineBounds;
}

bool rectComparator(Rect r1, Rect r2)
{
    return r1.x < r2.x;
}

int main(int argc, char **argv)
{
    std::string path = std::__fs::filesystem::absolute(argv[1]);
    std::string dir = std::__fs::filesystem::absolute(argv[1]).filename();

    std::ofstream fileOut;
    fileOut.open("./bud-csv/" + dir + "_raw.tsv");
    fileOut
        << "filename" << '\t'
        << "line_num" << '\t'
        << "text" << '\t'
        << "x" << '\t'
        << "y" << '\t'
        << "width" << '\t'
        << "height" << std::endl;

    tesseract::TessBaseAPI *tessOcr = new tesseract::TessBaseAPI();
    tessOcr->Init("./tessdata", "tha+digits_comma", tesseract::OEM_LSTM_ONLY);
    tessOcr->SetPageSegMode(tesseract::PSM_SINGLE_LINE);


    for (const auto &entry : std::__fs::filesystem::directory_iterator(path))
    {
        Mat im = imread(entry.path());
        Mat drawIm;

        if (im.empty())
            continue;

        im.copyTo(drawIm);
        std::vector<std::vector<Rect>> lines = lineBlock(im);

        if (lines.empty())
            continue;

        for (size_t i = 0; i < lines.size(); i++)
        {
            std::vector<Rect> rects = lines[i];
            std::sort(rects.begin(), rects.end(), rectComparator);
            for (Rect rect : rects)
            {
                Mat croped = im(rect);
                rectangle(drawIm, rect, Scalar(1));
                putText(
                    drawIm, std::to_string(rect.x) + "," + std::to_string(rect.y),
                    rect.tl(), FONT_HERSHEY_COMPLEX, .5, Scalar(1));
                tessOcr->SetImage(croped.data, croped.cols, croped.rows, 3, croped.step);
                std::string text = std::string(tessOcr->GetUTF8Text());

                while (!text.empty() && text.back() == '\n')
                    text.pop_back();

                fileOut
                    << std::string(entry.path().filename()) << '\t'
                    << std::to_string(i) << '\t'
                    << text << '\t'
                    << rect.x << '\t'
                    << rect.y << '\t'
                    << rect.width << '\t'
                    << rect.height << std::endl;
            }
        }

        std::string drawImPath =
            std::string(
                entry.path().parent_path().append("rects")) +
            "/" + std::string(entry.path().filename());
        imwrite(drawImPath, drawIm);
    }

    if (fileOut.is_open())
        fileOut.close();

    tessOcr->End();
    return EXIT_SUCCESS;
}