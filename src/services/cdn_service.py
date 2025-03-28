class CDNService:
    @staticmethod
    def get_widget_js() -> str:
        # This is the JavaScript code that will be served
        return """
console.log("Hello World");
""" 