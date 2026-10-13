from clean_dom import DOMCleaner

def main():
    raw_html = """
    <html>
      <head>
        <style>body { background: red; }</style>
        <script>console.log('analytics');</script>
      </head>
      <body>
        <div id="main" class="content" data-tracker="123">
          <h1 class="title">Hello World</h1>
          <a href="https://example.com" onclick="track()">Click Here</a>
        </div>
      </body>
    </html>
    """
    cleaner = DOMCleaner()
    print("=== Cleaned HTML ===")
    print(cleaner.clean(raw_html))

if __name__ == "__main__":
    main()