# Dockerfile — môi trường chạy Tool D (D0-PRE)
#
# Vì sao KHÔNG dùng thẳng freqtradeorg/freqtrade:stable:
#   1. Image gốc không có `git`. Ràng buộc 0d.5 của spec đòi git_sha trong
#      MỌI bản ghi kết quả — thiếu git thì khối xuất xứ 7+1 khoá không đầy đủ,
#      và L-Z40 fail mọi bản ghi.
#   2. Cần pytest để chạy bộ test khoá L-Zxx.
#   3. Bind mount Windows -> Linux làm lệch UID chủ sở hữu, git báo lỗi
#      "dubious ownership" và trả rỗng cho mọi lệnh — biến git_sha thành
#      "UNKNOWN" một cách ÂM THẦM. Đây đúng loại lỗi PHẦN 0d sinh ra để chặn.
#      Xử lý: `git config --system --add safe.directory`.
#
# Pin theo DIGEST, không dùng tag trôi "stable": spec (dòng 4442) đòi đọc mã
# nguồn Freqtrade ĐANG CÀI cho các giả định D2a/D2b/D6/D7 — với tag trôi thì
# "đang cài" đổi sau mỗi `docker pull`, và kết luận đọc mã nguồn mất giá trị.
#
# 🔴 QUAN TRỌNG: /freqtrade trong image là bản cài EDITABLE của chính Freqtrade
# (`pip show freqtrade` -> Editable project location: /freqtrade). TUYỆT ĐỐI
# không bind-mount repo của ta đè lên /freqtrade — sẽ xoá mất mã nguồn
# Freqtrade. Repo của ta mount vào /workspace (xem docker-compose.yml).
FROM freqtradeorg/freqtrade@sha256:7031bca43ed7668ebf421725dd5016acade6ef88b0771db3e08c96e6d19a42db

# Ghi lại phiên bản Freqtrade + git_sha nguồn của nó ngay ở layer image, để
# khoá xuất xứ thứ 8 (runtime_image_digest) và docs/freqtrade-source-read.md
# tra lại được mà không cần chạm mạng. Chạy khi CÒN LÀ ftuser (user mặc định
# của base image) vì `freqtrade` là script cài --user, chỉ chạy đúng dưới
# đúng user đó — chạy sau khi USER root thì "ModuleNotFoundError: freqtrade".
RUN freqtrade --version > /tmp/freqtrade_version.txt \
    && cp /freqtrade/freqtrade_commit /tmp/freqtrade_source_commit.txt

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && git config --system --add safe.directory /workspace \
    && mkdir -p /opt \
    && mv /tmp/freqtrade_version.txt /tmp/freqtrade_source_commit.txt /opt/ \
    && chmod 644 /opt/freqtrade_version.txt /opt/freqtrade_source_commit.txt

USER ftuser

# pytest: bộ test khoá L-Zxx. jsonschema/pyyaml đã có sẵn trong image
# (freqtrade tự cần), pin lại tường minh cho nhất quán với triết lý
# "mọi con số phải có xuất xứ" của project — không dựa vào "tình cờ đã có".
RUN pip install --no-cache-dir --user \
        pytest==9.1.1 \
        pyyaml==6.0.3 \
        jsonschema==4.26.0

# Repo của ta sống ở /workspace, KHÔNG PHẢI /freqtrade (xem cảnh báo ở trên).
WORKDIR /workspace
ENV PYTHONPATH=/workspace/src
ENV TZ=UTC
ENV PYTHONHASHSEED=0

# Bỏ ENTRYPOINT ["freqtrade"] kế thừa từ base image — service trong
# docker-compose.yml tự chọn entrypoint phù hợp (pytest / python / freqtrade).
ENTRYPOINT []
CMD ["python", "--version"]
