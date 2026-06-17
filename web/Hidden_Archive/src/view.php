<?php
ini_set('open_basedir', __DIR__ . '/uploads' . PATH_SEPARATOR . sys_get_temp_dir());

class FileViewer {
    private $blacklist = [
        'php', 'phtml', 'php3', 'php4', 'php5', 'php7', 'phar', 'inc',
        'sh', 'bash', 'pl', 'py', 'rb', 'asp', 'aspx', 'jsp'
    ];

    public function renderPage($inner) {
        echo "<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'>
<meta name='viewport' content='width=device-width,initial-scale=1.0'>
<title>SecureArchive - View</title>
<link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css'>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:#0a0e1a;color:#c0d0e0;padding:1rem;min-height:100vh}
pre{background:#0d1828;color:#4ac4ff;padding:.8rem;border-radius:6px;font-size:.85rem;white-space:pre-wrap;word-break:break-all;border:1px solid #1a3050;margin:0}
.navbar{background:#0d1528;border-bottom:1px solid #1a2a4e;padding:.6rem 1rem;margin:-1rem -1rem 1rem}
.navbar a{color:#e0e8f0!important;text-decoration:none;font-weight:700;font-size:1rem}
.navbar i{color:#4a9eff}
.card{background:#111e30;border:1px solid #1a3050;border-radius:10px;padding:1rem;max-width:800px;margin:0 auto}
.alert{background:#0a1e2a;color:#4ac4ff;border:1px solid #1a5a7a;border-radius:8px;padding:.6rem 1rem;margin:0}
.alert-danger{background:#2a0a12;color:#ff5a6a;border:1px solid #6a1a2a;border-radius:8px;padding:.6rem 1rem;margin:0}
.btn-download{display:inline-flex;align-items:center;gap:6px;background:linear-gradient(135deg,#1a8aba,#0a5a8a);color:#fff;border:none;border-radius:6px;padding:.5rem 1rem;font-weight:600;font-size:.85rem;text-decoration:none;cursor:pointer;transition:all .3s ease}
.btn-download:hover{transform:translateY(-1px);box-shadow:0 4px 15px #0a4a6a}
.btn-copy{display:inline-flex;align-items:center;gap:6px;background:#1a4a8a;color:#fff;border:none;border-radius:6px;padding:.5rem 1rem;font-weight:600;font-size:.85rem;cursor:pointer;transition:all .3s ease}
.btn-copy:hover{background:#2a6ad4;transform:translateY(-1px)}
.btn-copy.copied{background:#1a8a3a}
</style></head><body>
<script>
function copyLink(){var d=document.querySelector('.btn-download'),b=document.querySelector('.btn-copy');if(!d||!b)return;navigator.clipboard.writeText(window.location.origin+'/'+d.getAttribute('href')).then(function(){b.classList.add('copied');b.innerHTML='<i class=\"fas fa-check\"></i> Copied';setTimeout(function(){b.classList.remove('copied');b.innerHTML='<i class=\"fas fa-copy\"></i> Copy Link'},2000)})}
</script>
<div class='navbar'><a href='/'><i class='fas fa-shield-halved'></i> SecureArchive</a></div>
<div class='card'>$inner</div></body></html>";
    }

    public function view($filename) {
        $blocked_wrappers = [
            'php', 'file', 'data', 'http', 'ftp', 'phar', 'expect',
            'glob', 'ssh2', 'rar', 'ogg', 'zip', 'compress.bzip2',
            'https', 'input', 'tcp', 'udp', 'filter'
        ];
        foreach ($blocked_wrappers as $wrapper) {
            if (stripos($filename, $wrapper . '://') !== false) {
                $this->renderPage("<div class='alert-danger'>Hack detected!</div>");
                return;
            }
        }

        $ext = strtolower(pathinfo($filename, PATHINFO_EXTENSION));
        if(in_array($ext, $this->blacklist)) {
            $this->renderPage("<div class='alert-danger'>Access denied!</div>");
            return;
        }

        if(strlen($filename) > 100) {
            $this->renderPage("<div class='alert-danger'>Invalid filename length!</div>");
            return;
        }

        if(strpos($filename, '..') !== false) {
            $this->renderPage("<div class='alert-danger'>Directory traversal not allowed!</div>");
            return;
        }

        if(!file_exists($filename)) {
            $this->renderPage("<div class='alert-danger'>File not found!</div>");
            return;
        }

        if(isset($_GET['download'])) {
            $this->download($filename);
        }

        $dlLink = "view.php?file=" . urlencode($_GET['file']) . "&download=1";
        $buttons = "<div style='display:flex;gap:8px;margin-bottom:.6rem'>
<a href='$dlLink' class='btn-download'><i class='fas fa-download'></i> Download</a>
<button onclick='copyLink()' class='btn-copy'><i class='fas fa-copy'></i> Copy Link</button>
</div>";

        ob_start();
        include($filename);
        $content = ob_get_clean();
        $body = trim($content) !== '' ? "<pre>" . htmlspecialchars($content) . "</pre>" : "<div class='alert'>File is empty</div>";
        $this->renderPage($buttons . $body);
    }

    private function download($file) {
        $basename = basename($file);
        header('Content-Description: File Transfer');
        header('Content-Type: application/octet-stream');
        header('Content-Disposition: attachment; filename="' . $basename . '"');
        header('Content-Length: ' . filesize($file));
        readfile($file);
        exit;
    }
}

if(isset($_GET['file'])) {
    $viewer = new FileViewer();
    $viewer->view($_GET['file']);
} else {
    $viewer = new FileViewer();
    $viewer->renderPage("<div class='alert'>No file specified. Use <code>view.php?file=uploads/file.zip</code></div>");
}
