#include <cstdlib>
#include <memory>
#include <string>

#include "cyber/component/timer_component.h"
#include "cyber/cyber.h"
#include "wheelos_msgs/sensor_msgs/sensor_image.pb.h"

class SyntheticSensor : public apollo::cyber::TimerComponent {
 public:
  bool Init() override {
    const char* topic = std::getenv("SENSOR_INFRA_TEST_TOPIC");
    if (topic == nullptr ||
        std::string(topic).find("/sensor_infra/test/") != 0) {
      AERROR << "Synthetic sensor requires an isolated test topic";
      return false;
    }
    writer_ = node_->CreateWriter<apollo::drivers::Image>(topic);
    return writer_ != nullptr;
  }

  void Shutdown() override { AINFO << "Cleanup synthetic sensor"; }

 private:
  bool Proc() override {
    auto image = std::make_shared<apollo::drivers::Image>();
    image->mutable_header()->set_timestamp_sec(
        apollo::cyber::Time::Now().ToSecond());
    image->set_frame_id("synthetic");
    image->set_height(1);
    image->set_width(2);
    image->set_step(2);
    image->set_encoding("mono8");
    image->set_data("AB");
    return writer_->Write(image);
  }

  std::shared_ptr<apollo::cyber::Writer<apollo::drivers::Image>> writer_;
};

CYBER_REGISTER_COMPONENT(SyntheticSensor)
