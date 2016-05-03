<?php

$req_dump = print_r($_REQUEST, TRUE);
$fp = fopen('/tmp/request.log', 'a');
fwrite($fp, $req_dump);
fclose($fp);

$caller=$_POST['caller'];
$called=$_POST['called'];
$number=$_POST['number'];
 
//if (isset($_FILES['record']))
{                   
 //if (file_exists($_FILES['record']['tmp_name']) && is_uploaded_file($_FILES['record']['tmp_name']) )
 
 $infile=$_FILES['record']['tmp_name'];
 // Allow the rigths for Apache if you want to keep the recording on the server
 $outfile="/var/www/".$caller.".mp3";
 @unlink($outfile);
 system("ffmpeg -i $infile -ab 8k $outfile");
 }
 

?>