library(jsonlite)
library(ggplot2)

data_dir <- "/Users/williamydh/Library/Mobile Documents/com~apple~CloudDocs/Sync_iCloud/Career/WT/Phoenix_Capital/Quant/kalshi_tracker/data/kalshi_trades"
output_dir <- "/Users/williamydh/Library/Mobile Documents/com~apple~CloudDocs/Sync_iCloud/Career/WT/Phoenix_Capital/Quant/kalshi_tracker/analysis"

if (!dir.exists(output_dir)) {
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
}

trade_files <- sort(list.files(data_dir, pattern = "\\.json$", full.names = TRUE))

if (length(trade_files) == 0) {
  stop("No trade files found in ", data_dir)
}

compute_daily_volume <- function(file_path) {
  payload <- fromJSON(file_path, simplifyVector = FALSE)
  date <- as.Date(payload$date)
  trades <- payload$trades
  total_volume <- sum(vapply(trades, function(trade) trade$count, numeric(1)))
  data.frame(date = date, total_volume = total_volume)
}

daily_volumes <- do.call(
  rbind,
  lapply(trade_files, compute_daily_volume)
)

daily_volumes <- daily_volumes[order(daily_volumes$date), ]
rownames(daily_volumes) <- NULL

rolling_window <- 7
rolling_total <- vapply(
  seq_len(nrow(daily_volumes)),
  function(idx) {
    start_idx <- max(1, idx - rolling_window + 1)
    sum(daily_volumes$total_volume[start_idx:idx])
  },
  numeric(1)
)

daily_volumes$rolling_total <- rolling_total

write.csv(daily_volumes, file = file.path(output_dir, "daily_total_volume.csv"), row.names = FALSE)

format_millions <- function(x) {
  paste0(format(round(x / 1e6, 1), nsmall = 1), "M")
}

plot_path <- file.path(output_dir, "7d_rolling_total_volume.png")

plt <- ggplot(daily_volumes, aes(x = date, y = rolling_total)) +
  geom_line(color = "#0b3d91", linewidth = 1.1) +
  geom_point(color = "#0b3d91", size = 1.9) +
  labs(
    title = "7-Day Rolling Total Trading Volume",
    x = "Date",
    y = "7-Day Total Volume (Contracts)"
  ) +
  scale_y_continuous(labels = format_millions) +
  theme_minimal(base_size = 14) +
  theme(
    panel.grid.major = element_line(color = "grey85"),
    panel.grid.minor = element_blank(),
    plot.title = element_text(face = "bold")
  )

ggsave(plot_path, plt, width = 14, height = 9, dpi = 150)

message("Daily totals saved to: ", file.path(output_dir, "daily_total_volume.csv"))
message("7-day rolling total chart saved to: ", plot_path)

