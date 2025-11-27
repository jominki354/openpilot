#include "selfdrive/ui/qt/screenrecorder/screenrecorder.h"
#include "selfdrive/ui/qt/util.h"
#include <QPainter>

ScreenRecoder::ScreenRecoder(QWidget *parent) : QPushButton(parent) {
  const int size = 190;
  setFixedSize(size, size);
  setFocusPolicy(Qt::NoFocus);

  joystick_img = QPixmap("../assets/img_joystick.png");
  joystick_mode = params.getBool("JoystickDebugMode");

  QObject::connect(this, &QPushButton::clicked, [=]() { toggle(); });
}

void ScreenRecoder::toggle() {
  joystick_mode = !joystick_mode;
  params.putBool("JoystickDebugMode", joystick_mode);
  update();
}

void ScreenRecoder::update_screen() {
  // Poll params occasionally to sync state if changed externally
  static int frame = 0;
  if (frame++ % 50 == 0) {
    bool new_mode = params.getBool("JoystickDebugMode");
    if (new_mode != joystick_mode) {
      joystick_mode = new_mode;
      update();
    }
  }
}

void ScreenRecoder::paintEvent(QPaintEvent *event) {
  QPainter p(this);
  p.setRenderHint(QPainter::Antialiasing);

  QPoint center(width() / 2, height() / 2);

  // Background
  QColor bg(joystick_mode ? "#33Ab4C" : "#393939"); // Green if ON, Gray if OFF
  if (isDown()) {
    bg = bg.darker(120);
  }
  p.setPen(Qt::NoPen);
  p.setBrush(bg);
  p.drawEllipse(center, 85, 85);

  // Image
  if (!joystick_img.isNull()) {
    p.drawPixmap(center.x() - joystick_img.width() / 2, center.y() - joystick_img.height() / 2 - 10, joystick_img);
  }

  // Text
  p.setFont(InterFont(25, QFont::Bold));
  p.setPen(Qt::white);
  QString text = joystick_mode ? "ON" : "OFF";
  p.drawText(rect().adjusted(0, 0, 0, -25), Qt::AlignBottom | Qt::AlignHCenter, text);
}
