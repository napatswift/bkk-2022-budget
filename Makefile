main:
	g++ -O3 -std=c++11 to_text.cpp `pkg-config --cflags --libs tesseract opencv4` -o to_text.o
