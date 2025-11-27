#pragma once

#include <QPushButton>
#include "common/params.h"

class ScreenRecoder : public QPushButton {
  Q_OBJECT

public:
  ScreenRecoder(QWidget *parent = 0);
  virtual ~ScreenRecoder() {}

  void update_screen();
  void toggle();
  void start() {}
  void stop() {}

protected:
  void paintEvent(QPaintEvent*) override;

private:
  Params params;
  QPixmap joystick_img;
  bool joystick_mode;
};
