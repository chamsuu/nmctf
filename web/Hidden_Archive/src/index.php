<?php
ini_set('open_basedir', __DIR__ . '/uploads' . PATH_SEPARATOR . sys_get_temp_dir());

foreach(glob(__DIR__ . '/uploads/*') as $f) {
    if(is_file($f) && time() - filemtime($f) > 600) unlink($f);
}

class SecurityFilter {
    private $blacklist = [
        '<script', '<%', '<asp',
        'eval', 'assert', 'system', 'shell_exec', 'exec', 'passthru',
        'base64_decode', 'gzinflate', 'str_rot13',
        'data://', 'file://', 'glob://', 'phar://', 'ssh2://', 'rar://', 'ogg://', 'expect://', 'zip://', 'input://',
        'cat', 'head', 'tail', 'env', 'ls', 'cp', 'mv', 'rm', 'chmod', 'chown',
        'nc', 'ncat', 'bash', 'sh', 'python', 'perl',
        'wget', 'curl', 'netcat', 'socat', 'telnet','find ',
         'grep', 'awk', 'sed', 'sort', 'cut',
        'fla', 'flag', 'passwd', 'shadow', 'config'
    ];

    public function checkContent($file) {
        $content = file_get_contents($file);
        foreach($this->blacklist as $str) {
            if(stripos($content, $str) !== false) {
                return false;
            }
        }
        return true;
    }
}

class ArchiveValidator {
    private $magicNumbers = [
        'zip' => "\x50\x4B\x03\x04",
        'gz'  => "\x1F\x8B",
        'bz2' => "\x42\x5A\x68",
        '7z'  => "\x37\x7A\xBC\xAF\x27\x1C",
        'rar' => "\x52\x61\x72\x21",
        'tar' => "\x75\x73\x74\x61\x72",
        'xz'  => "\xFD\x37\x7A\x58\x5A\x00",
        'lzma'=> "\x5D\x00\x00",
        'cab' => "\x4D\x53\x43\x46",
        'arj' => "\x60\xEA",
        'z'   => "\x1F\x9D"
    ];

    public function isValid($file, $extension) {
        $extension = strtolower($extension);
        if (!isset($this->magicNumbers[$extension])) {
            return false;
        }

        $handle = fopen($file, 'rb');
        if (!$handle) {
            return false;
        }

        $magic = fread($handle, strlen($this->magicNumbers[$extension]));
        fclose($handle);

        return $magic === $this->magicNumbers[$extension];
    }
}

class FileShare {
    private $uploadPath = "uploads/";
    private $maxSize = 1048576;
    private $allowedExtensions = [
        'zip', 'gz', 'bz2', '7z', 'rar', 'tar',
        'xz', 'lz', 'lzma', 'tgz', 'tbz2', 'tlz',
        'cab', 'gzip', 'bzip2', 'lzip', 'lzop',
        'arc', 'arj', 'z'
    ];
    private $validator;
    private $securityFilter;

    public function __construct() {
        $this->validator = new ArchiveValidator();
        $this->securityFilter = new SecurityFilter();
        if(!is_dir($this->uploadPath)) {
            mkdir($this->uploadPath, 0750, true);
        }
    }

    public function upload($file) {
        if(!isset($file['tmp_name']) || !isset($file['name'])) {
            return "Invalid file upload";
        }

        if($file['size'] > $this->maxSize) {
            return "File too large! Max size is 1MB";
        }

        $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
        if(!in_array($ext, $this->allowedExtensions)) {
            return "Only compressed archives allowed!";
        }

        if(!$this->validator->isValid($file['tmp_name'], $ext)) {
            return "Invalid archive format!";
        }

        if(!$this->securityFilter->checkContent($file['tmp_name'])) {
            return "Malicious content detected!";
        }

        $newName = bin2hex(random_bytes(16)) . '.' . $ext;
        $destination = $this->uploadPath . $newName;

        if(!move_uploaded_file($file['tmp_name'], $destination)) {
            return "Upload failed!";
        }

        chmod($destination, 0440);
        return "File uploaded successfully as: " . $newName;
    }
}

$alert = null;
if(isset($_FILES['file'])) {
    $share = new FileShare();
    $result = $share->upload($_FILES['file']);
    $alertType = strpos($result, 'success') !== false ? 'success' : 'danger';
    $msg = $result;
    if($alertType === 'success') {
        $name = substr($result, strrpos($result, ' ') + 1);
        $link = "view.php?file=uploads/$name";
        $msg = "Uploaded! <a href='$link' style='color:#4ac4ff' id='uploadLink'>$link</a>
            <button onclick='copyLink()' class='btn-copy'><i class='fas fa-copy'></i></button>";
    }
    $alert = ['type' => $alertType, 'message' => $msg];
}

if(isset($_GET['file'])) {
    header('Location: view.php?file=' . urlencode($_GET['file']));
    exit;
}

function renderAlert($alert) {
    if(!$alert) return '';
    $icon = $alert['type'] === 'success' ? 'check-circle' : 'exclamation-circle';
    return "<div class='alert alert-{$alert['type']}'>
        <i class='fas fa-$icon'></i> {$alert['message']}
    </div>";
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SecureArchive</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:#0a0e1a;min-height:100vh;color:#c0d0e0}
.navbar{background:#0d1528!important;border-bottom:1px solid #1a2a4e;padding:.5rem 0}
.navbar-brand{font-weight:700;font-size:1.1rem;letter-spacing:-.5px;color:#e0e8f0!important}
.navbar-brand i{color:#4a9eff}
.container{max-width:600px;margin:0 auto;padding:1rem 1rem}
.card{background:#111e30;border:1px solid #1a3050;border-radius:10px;overflow:hidden;margin-bottom:.8rem}
.card-header{padding:.6rem 1rem;font-weight:600;font-size:.9rem;border-bottom:1px solid #1a3050}
.card-header.upload{background:linear-gradient(135deg,#1a4a8a,#0d2b5e)}
.card-header.view{background:linear-gradient(135deg,#0d5e8a,#0a3a5e)}
.card-body{padding:.8rem 1rem}
.upload-area{border:1.5px dashed #2a4a6a;border-radius:8px;padding:1rem;text-align:center;background:#0d1828;transition:all .3s ease;cursor:pointer}
.upload-area:hover{border-color:#4a9eff;background:#0d1e38}
.upload-area i{color:#4a9eff;margin-bottom:.5rem;font-size:1.5rem}
.upload-area h5{color:#d0dce8;margin-bottom:.3rem;font-size:.95rem}
.upload-area small{color:#5a7a9a;font-size:.8rem}
.form-control{background:#0d1828;border:1px solid #2a4a6a;border-radius:6px;color:#d0dce8;padding:.5rem .8rem;transition:all .3s ease;font-size:.9rem}
.form-control:focus{background:#0d1e38;border-color:#4a9eff;color:#fff;box-shadow:0 0 0 2px #1a3a6a}
.form-control::placeholder{color:#4a6a8a}
.form-label{color:#7a9aba;font-weight:500;margin-bottom:.3rem;font-size:.85rem}
.btn{border:none;border-radius:6px;padding:.5rem 1rem;font-weight:600;transition:all .3s ease;width:100%;cursor:pointer;font-size:.9rem}
.btn-upload{background:linear-gradient(135deg,#2a6ad4,#1a4a9a);color:#fff}
.btn-upload:hover{transform:translateY(-1px);box-shadow:0 4px 15px #1a3a7a}
.btn-view{background:linear-gradient(135deg,#1a8aba,#0a5a8a);color:#fff}
.btn-view:hover{transform:translateY(-1px);box-shadow:0 4px 15px #0a4a6a}
.alert{border-radius:8px;padding:.6rem 1rem;border:none;font-weight:500;font-size:.85rem}
.alert-success{background:#0a1e2a;color:#4ac4ff;border:1px solid #1a5a7a}
.alert-danger{background:#2a0a12;color:#ff5a6a;border:1px solid #6a1a2a}
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-shield-halved"></i> SecureArchive
            </a>
        </div>
    </nav>

    <div class="container">
        <?= renderAlert($alert) ?>

        <div class="card">
            <div class="card-header upload">
                <i class="fas fa-cloud-arrow-up"></i> Upload Archive
            </div>
            <div class="card-body">
                <form action="" method="post" enctype="multipart/form-data">
                    <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                        <i class="fas fa-file-archive fa-3x"></i>
                        <h5>Drop archive here or click to browse</h5>
                        <small>Supported: zip, gz, bz2, 7z, rar, tar, xz, cab, arj, z</small>
                        <input type="file" id="fileInput" class="form-control mt-3" name="file" required hidden>
                    </div>
                    <button type="submit" class="btn btn-upload mt-3">
                        <i class="fas fa-upload"></i> Upload
                    </button>
                </form>
            </div>
        </div>

        
    </div>
</body>
</html>
