client = GitHubAppClient(os.getenv("AUTH_CLIENT_ID", "Ov23liqGYUmCNyzygLro"), 
                         os.getenv("AUTH_CLIENT_SECRET"), "59737f7da006a5a6abc325cad2158bf3726e79b9")
auth_callback_path = "/auth_redirect"
