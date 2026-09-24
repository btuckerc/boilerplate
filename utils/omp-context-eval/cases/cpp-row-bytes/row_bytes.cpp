#include <cstddef>
#include <iostream>
#include <limits>

std::size_t row_bytes(std::size_t width, std::size_t bits_per_pixel) {
    // Intentional bug: multiplication and rounding can overflow.
    return (width * bits_per_pixel + 7) / 8;
}

int main() {
    const std::size_t max = std::numeric_limits<std::size_t>::max();
    std::cout << row_bytes(0, 16) << "\n"
              << row_bytes(1, 1) << "\n"
              << row_bytes(7, 1) << "\n"
              << row_bytes(8, 1) << "\n"
              << row_bytes(9, 1) << "\n"
              << row_bytes(3, 24) << "\n"
              << row_bytes(max, 0) << "\n"
              << row_bytes(max, 1) << "\n";
}
