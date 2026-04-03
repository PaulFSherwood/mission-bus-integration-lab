UNAME_S := $(shell uname -s)

CXX = g++
CXXFLAGS = -std=c++20 -Wall -Wextra -I/usr/include/eigen3
LDFLAGS =
ASAN ?= 0

# --- Platform specific flags ---
ifeq ($(UNAME_S),Linux)		# Linux
	# --- CXXFLAGS += $(shell pkg-config --cflags sdl2 SDL2_ttf SDL2_image)
	# --- LDFLAGS  += $(shell pkg-config --libs sdl2 SDL2_ttf SDL2_image)
	CXXFLAGS += $(shell pkg-config --cflags)
	LDFLAGS  += $(shell pkg-config --libs)
endif

ifeq ($(UNAME_S),Darwin) 	# macOS
	CXXFLAGS += -I/opt/homebrew/include/SDL2
	LDFLAGS += -L/opt/homebrew/lib -lSDL2 -lSDL2_ttf -lSDL2_image
endif

ifeq ($(OS),Windows_NT)		# Windows (MinGW cross-compile or native MSYS2)
    CXX = x86_64-w64-mingw32-g++
    CXXFLAGS += -IC:/SDL2/include
    LDFLAGS  += -LC:/SDL2/lib -lmingw32 -lSDL2main -lSDL2 -lSDL2_ttf -lSDL2_image
endif

# AddressSanitizer toggle (kept separate from release/debug opts)
ifeq ($(ASAN),1)
  CXXFLAGS += -g -O1 -fno-omit-frame-pointer -fsanitize=address -D_GLIBCXX_ASSERTIONS
  LDFLAGS  += -fsanitize=address
endif

# --- Project structure ---
SOURCES = \
    tools.cpp \
    main.cpp

OBJECTS = $(SOURCES:.cpp=.o)
TARGET = modernCPP 

all: release

release: CXXFLAGS += -O2
release: $(TARGET)

debug: CXXFLAGS += -O0 -g -DDEBUG
debug: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)
	@echo "\033[1;32m✅ Build complete: $(TARGET) ✅\033[0m"
	rm -f $(OBJECTS)

run: $(TARGET)
	./$(TARGET)

play: all
	./$(TARGET)

clean:
	rm -f $(OBJECTS) $(TARGET)
	@echo "✝ I have Exercised the demons, this house is clean."

.PHONY: all clean run play debug
