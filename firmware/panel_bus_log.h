#pragma once

#include "esphome/components/web_server_base/web_server_base.h"
#include "esphome/components/web_server_idf/web_server_idf.h"

#include <array>
#include <cstdio>
#include <memory>
#include <new>

class PanelBusLog : public AsyncWebHandler {
 public:
  void record(uint32_t ms, char direction, uint8_t byte) {
    portENTER_CRITICAL(&lock_);
    if (count_ == 0 || direction != entries_[head_].direction ||
        entries_[head_].size == entries_[head_].data.size() || ms - entries_[head_].ms >= 5) {
      head_ = (head_ + 1) % capacity;
      if (count_ < capacity) ++count_;
      entries_[head_] = Entry{ms, direction, 0, {}};
    }
    auto &entry = entries_[head_];
    entry.data[entry.size++] = byte;
    portEXIT_CRITICAL(&lock_);
  }

  bool canHandle(AsyncWebServerRequest *request) const override {
    std::array<char, AsyncWebServerRequest::URL_BUF_SIZE> url;
    return request->method() == HTTP_GET && request->url_to(url) == "/bus-log";
  }

  void handleRequest(AsyncWebServerRequest *request) override {
    std::unique_ptr<Entry[]> snapshot(new (std::nothrow) Entry[capacity]);
    if (!snapshot) {
      request->send(503, "text/plain", "Insufficient memory for bus log");
      return;
    }
    portENTER_CRITICAL(&lock_);
    const size_t count = count_;
    const size_t first = (head_ + capacity + 1 - count) % capacity;
    for (size_t i = 0; i < count; ++i) snapshot[i] = entries_[(first + i) % capacity];
    portEXIT_CRITICAL(&lock_);

    httpd_req_t *req = *request;
    httpd_resp_set_type(req, "text/plain; charset=utf-8");
    httpd_resp_set_hdr(req, "Cache-Control", "no-store");
    httpd_resp_set_hdr(req, "Content-Disposition", "attachment; filename=rs485.log");
    constexpr char header[] = "# uptime_ms direction hex (T = queued to UART)\n";
    if (httpd_resp_send_chunk(req, header, sizeof(header) - 1) != ESP_OK) return;
    constexpr char hex[] = "0123456789ABCDEF";
    for (size_t i = 0; i < count; ++i) {
      const auto &entry = snapshot[i];
      char line[128];
      char *end = line + std::snprintf(line, sizeof(line), "%lu %c", static_cast<unsigned long>(entry.ms),
                                       entry.direction);
      for (size_t j = 0; j < entry.size; ++j) {
        const uint8_t byte = entry.data[j];
        *end++ = ' ';
        *end++ = hex[byte >> 4];
        *end++ = hex[byte & 0x0F];
      }
      *end++ = '\n';
      if (httpd_resp_send_chunk(req, line, end - line) != ESP_OK) return;
    }
    httpd_resp_send_chunk(req, nullptr, 0);
  }

 private:
  struct Entry {
    uint32_t ms;
    char direction;
    uint8_t size;
    std::array<uint8_t, 32> data;
  };
  static constexpr size_t capacity = 256;
  std::array<Entry, capacity> entries_{};
  size_t head_ = capacity - 1;
  size_t count_ = 0;
  portMUX_TYPE lock_ = portMUX_INITIALIZER_UNLOCKED;
};

static PanelBusLog panel_bus_log;
