import time

from clean_dom import DOMCleaner


def run_benchmark():
    # Ένα τυπικό, "φουσκωμένο" HTML από scraping πραγματικής ιστοσελίδας
    bloated_html = """
    <html>
      <head>
        <style>
          body { background-color: #f0f0f0; margin: 0; padding: 20px; font-family: sans-serif; }
          .ad-banner { display: none; width: 100%; height: 90px; background: red; }
          .tracker-pixel { position: absolute; left: -9999px; }
        </style>
        <script src="https://analytics.example.com/track.js"></script>
        <script src="https://ads.example.com/bidder.js"></script>
        <meta name="robots" content="noindex">
        <link rel="stylesheet" href="styles.css">
      </head>
      <body>
        <div class="ad-banner">Advertisement</div>
        <div class="tracker-pixel"><img src="tracker.gif" width="1" height="1"></div>
        
        <div id="main-content" class="container" data-tracking-id="982347-abc" style="margin-top: 10px;">
          <h1 class="title" onclick="trackClick('main-title')">Optimizing LLM Context Windows</h1>
          <p class="description" style="color: #333; line-height: 1.5;">
            Web scraping for LLMs often brings massive amounts of boilerplate code, tracking scripts, 
            and styling fluff that wastes precious context tokens and increases API costs.
          </p>
          <a href="https://example.com/read-more" class="btn primary" data-analytics="click-event">Read Full Article</a>
        </div>
        
        <div class="footer-links" style="display: flex; gap: 10px;">
          <a href="/privacy">Privacy Policy</a>
          <a href="/terms">Terms of Service</a>
        </div>
      </body>
    </html>
    """
    
    cleaner = DOMCleaner()
    
    # Μέτρηση μεγέθους πριν και μετά
    original_size = len(bloated_html)
    
    start_time = time.time()
    cleaned_html = cleaner.clean(bloated_html)
    elapsed_time = (time.time() - start_time) * 1000 # σε milliseconds
    
    cleaned_size = len(cleaned_html)
    reduction_percentage = ((original_size - cleaned_size) / original_size) * 100

    print("=" * 50)
    print(" 📊 CLEAN-DOM PERFORMANCE & TOKEN REDUCTION BENCHMARK")
    print("=" * 50)
    print(f"• Original HTML Size : {original_size} characters")
    print(f"• Cleaned HTML Size  : {cleaned_size} characters")
    print(f"• Size Reduction     : {reduction_percentage:.2f}% 🚀")
    print(f"• Processing Time    : {elapsed_time:.3f} ms")
    print("=" * 50)

if __name__ == "__main__":
    run_benchmark()