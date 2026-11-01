#include <iostream>

#include "cyber/record/record_reader.h"
#include "wheelos_msgs/sensor_msgs/sensor_image.pb.h"

int main(int argc, char** argv) {
  if (argc != 3) {
    std::cerr << "usage: record_probe RECORD IMAGE_TOPIC\n";
    return 2;
  }
  apollo::cyber::record::RecordReader reader(argv[1]);
  if (!reader.IsValid() || reader.GetProtoDesc(argv[2]).empty()) {
    std::cerr << "invalid record or missing image descriptor\n";
    return 1;
  }
  apollo::cyber::record::RecordMessage message;
  int received = 0;
  while (reader.ReadMessage(&message)) {
    apollo::drivers::Image image;
    if (message.channel_name != argv[2] ||
        !image.ParseFromString(message.content) || !image.has_header() ||
        image.frame_id() != "synthetic" || image.height() != 1 ||
        image.width() != 2 || image.step() != 2 ||
        image.encoding() != "mono8" || image.data() != "AB") {
      std::cerr << "unexpected channel or invalid synthetic image payload\n";
      return 1;
    }
    ++received;
  }
  std::cout << "{\"recorded_images_verified\":" << received << "}\n";
  return received >= 5 ? 0 : 1;
}
