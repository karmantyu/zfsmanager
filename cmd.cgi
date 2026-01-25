#!/usr/bin/perl

require './zfsmanager-lib.pl';
ReadParse();
ui_print_header(undef, $text{'cmd_title'}, "", undef, 1, 0);

if ($text{$in{'cmd'}."_desc"}) { 
	print ui_table_start($text{$in{'cmd'}."_cmd"}, "width=100%", "10", ['align=left'] );
	print ui_table_row($text{'cmd_dscpt'}, $text{$in{'cmd'}."_desc"});
	print ui_table_end();
};

print ui_table_start($text{'cmd_title'}, "width=100%", "10", ['align=left'] );
	
if ($in{'cmd'} =~ "setzfs") {
	$in{'confirm'} = "yes";
	my $q_prop = quotemeta($in{'property'});
	my $q_set = quotemeta($in{'set'});
	my $q_zfs = quotemeta($in{'zfs'});
	$q_zfs =~ s/\\\//\//g;
	$q_zfs =~ s/\\([.:\-])/$1/g;
	$q_prop =~ s/\\([.:\-])/$1/g;
	$q_set =~ s/\\([.:\-])/$1/g;
	if (($in{'set'} =~ "inherit") && ($config{'zfs_properties'} =~ /1/)) { $cmd = "zfs inherit $q_prop $q_zfs"; 
	} elsif ($config{'zfs_properties'} =~ /1/) { $cmd =  "zfs set $q_prop=$q_set $q_zfs"; }
	ui_cmd("$in{'property'} to $in{'set'} on $in{'zfs'}", $cmd);
}
elsif ($in{'cmd'} =~ "setpool")  {
	$in{'confirm'} = "yes";
	my $q_prop = quotemeta($in{'property'});
	my $q_set = quotemeta($in{'set'});
	my $q_pool = quotemeta($in{'pool'});
	$q_prop =~ s/\\([.:\-])/$1/g;
	$q_set =~ s/\\([.:\-])/$1/g;
	$q_pool =~ s/\\([.:\-])/$1/g;
	if ($in{'property'} =~ 'comment') { $q_set = '"'.$q_set.'"'; }
	my $cmd = ($config{'pool_properties'} =~ /1/) ? "zpool set $q_prop=$q_set $q_pool": undef;
	ui_cmd("$in{'property'} to $in{'set'} in $in{'pool'}", $cmd);
}
elsif ($in{'cmd'} =~ "snapshot")  {
	my $q_zfs = quotemeta($in{'zfs'});
	$q_zfs =~ s/\\\//\//g;
	$q_zfs =~ s/\\([.:\-])/$1/g;
	my $q_snap = quotemeta($in{'snap'});
	$q_snap =~ s/\\([.:\-])/$1/g;
	my $cmd = "zfs snapshot ".$q_zfs."@".$q_snap;
	$in{'confirm'} = "yes";
	ui_cmd($in{'snap'}, $cmd);
	print "", (!$result[1]) ? ui_list_snapshots($in{'zfs'}."@".$in{'snap'}) : undef;
}
elsif ($in{'cmd'} =~ "send") {
	if (!$in{'dest'}) {
                print $text{'cmd_send'}." ".$in{'snap'}." ".$text{'cmd_gzip'}."  <br />";
                print "<br />";
                print ui_form_start('cmd.cgi', 'post');
                print ui_hidden('cmd', $in{'cmd'});
		print ui_hidden('snap', $in{'snap'});
		my $newfile = $in{'snap'} =~ s![/@]!_!gr;
		print "<b>$text{'destination'} </b>".ui_filebox('dest', $config{'last_send'}, 35, undef, undef, undef, 1)."<br />";
		print "<b>$text{'filename'} </b>".ui_textbox('file', $newfile.'.gz', 50)."<br />";
		print ui_submit($text{'continue'}, undef, undef);
                print ui_form_end();
	} else { 
		$in{'confirm'} = "yes";
		my $q_snap = quotemeta($in{'snap'});
		$q_snap =~ s/\\\//\//g;
		$q_snap =~ s/\\@/@/g;
		$q_snap =~ s/\\([.:\-])/$1/g;
		my $q_dest = quotemeta($in{'dest'});
		$q_dest =~ s/\\([.:\-])/$1/g;
		my $q_file = quotemeta($in{'file'});
		$q_file =~ s/\\([.:\-])/$1/g;
		my $cmd = "zfs send ".$q_snap." | gzip > ".$q_dest."/".$q_file;
		ui_cmd($in{'snap'}, $cmd);
		$config{'last_send'} = $in{'dest'};
		save_module_config();
		print `ls -al $in{'dest'}'."/".$in{'file'}`;
	}
}
elsif ($in{'cmd'} =~ "createzfs")  {
	my %createopts = create_opts();
	my %options = ();
	foreach $key (sort (keys %createopts)) {
		$options{$key} = ($in{$key}) ? quotemeta($in{$key}) : undef;
		if ($options{$key}) { $options{$key} =~ s/\\([.:\-])/$1/g; }
	}
	if ($in{'mountpoint'}) { 
		$options{'mountpoint'} = quotemeta($in{'mountpoint'}); 
		$options{'mountpoint'} =~ s/\\\//\//g;
		$options{'mountpoint'} =~ s/\\([.:\-])/$1/g;
	}
	if ($in{'zvol'} == '1') { 
		$options{'zvol'} = quotemeta($in{'size'});
		$options{'sparse'} = $in{'sparse'};
		$options{'volblocksize'} = quotemeta($in{'volblocksize'});
		foreach my $k ('logbias', 'primarycache', 'secondarycache', 'refreservation') {
			if ($in{$k}) { 
				$options{$k} = quotemeta($in{$k}); 
				$options{$k} =~ s/\\([.:\-])/$1/g;
			}
		}
	} 
	my $q_parent = quotemeta($in{'parent'});
	$q_parent =~ s/\\\//\//g;
	$q_parent =~ s/\\([.:\-])/$1/g;
	my $q_zfs = quotemeta($in{'zfs'});
	$q_zfs =~ s/\\([.:\-])/$1/g;
	my $cmd = ($in{'parent'}) ? cmd_create_zfs($q_parent."/".$q_zfs, \%options) : undef;
	$in{'confirm'} = "yes";
	ui_cmd("$in{'parent'}/$in{'zfs'}", $cmd);
	#print "", (!$result[1]) ? ui_zfs_list($in{'zfs'}) : undef;
	#^^^this doesn't work for some reason
	@footer = ("status.cgi?zfs=".$in{'parent'}."/".$in{'zfs'}."&xnavigation=1", $in{'parent'}."/".$in{'zfs'});
}
elsif ($in{'cmd'} =~ "clone")  {
	my %createopts = create_opts();
	$opts = ();
	foreach $key (sort (keys %createopts))
	{
		if ($in{$key})
		{
			my $val = quotemeta($in{$key});
			$val =~ s/\\([.:\-])/$1/g;
			$opts = ($in{$key} =~ 'default') ? $opts : $opts.' -o '.$key.'='.$val;
		}
	}
	if ($in{'mountpoint'}) { 
		my $q_mp = quotemeta($in{'mountpoint'});
		$q_mp =~ s/\\\//\//g;
		$q_mp =~ s/\\([.:\-])/$1/g;
		$opts .= ' -o mountpoint='.$q_mp; 
	}
	$in{'confirm'} = "yes";
	my $q_clone = quotemeta($in{'clone'});
	$q_clone =~ s/\\\//\//g;
	$q_clone =~ s/\\@/@/g;
	$q_clone =~ s/\\([.:\-])/$1/g;
	my $q_parent = quotemeta($in{'parent'});
	$q_parent =~ s/\\\//\//g;
	$q_parent =~ s/\\([.:\-])/$1/g;
	my $q_zfs = quotemeta($in{'zfs'});
	$q_zfs =~ s/\\([.:\-])/$1/g;
	my $cmd = "zfs clone ".$q_clone." ".$q_parent.'/'.$q_zfs." ".$opts;
	ui_cmd($in{'clone'}, $cmd);
	@footer = ("status.cgi?snap=".$in{'clone'}."&xnavigation=1", $in{'clone'})
}
elsif ($in{'cmd'} =~ "rename")  {
	my $q_zfs = quotemeta($in{'zfs'});
	$q_zfs =~ s/\\\//\//g;
	$q_zfs =~ s/\\@/@/g;
	$q_zfs =~ s/\\([.:\-])/$1/g;
	my $q_parent = quotemeta($in{'parent'});
	$q_parent =~ s/\\\//\//g;
	$q_parent =~ s/\\([.:\-])/$1/g;
	my $q_name = quotemeta($in{'name'});
	$q_name =~ s/\\([.:\-])/$1/g;
	my $q_force = ($in{'force'} && $in{'force'} =~ /-f/) ? "-f " : "";
	my $q_recurse = ($in{'recurse'} && $in{'recurse'} =~ /-r/) ? "-r " : "";
	my $q_prnt = ($in{'prnt'} && $in{'prnt'} =~ /-p/) ? "-p " : "";
	if (index($in{'zfs'}, '@') != -1) { 
		$cmd = "zfs rename ".$q_force.$q_recurse.$q_zfs." ".$q_parent.'@'.$q_name;
		@footer = ('status.cgi?snap='.$in{'parent'}.'@'.$in{'name'}.'&xnavigation=1', $in{'parent'}.'@'.$in{'name'});
	} elsif (index($in{'zfs'}, '/') != -1) { 
		$cmd = "zfs rename ".$q_force.$q_prnt.$q_zfs." ".$q_parent.'/'.$q_name;
		if ($in{'confirm'}) { @footer = ('status.cgi?zfs='.$in{'parent'}.'/'.$in{'name'}.'&xnavigation=1', $in{'parent'}.'/'.$in{'name'}); }
	}
	print ui_table_end();
	ui_cmd($in{'zfs'}." to ".$in{'name'}, $cmd);
	print ui_table_start($text{'cmd_title'}, "width=100%", "10", ['align=left'] );
}
elsif ($in{'cmd'} =~ "createzpool")  {
	my %createopts = create_opts();
	my %options = ();
	$in{'volblocksize'} = "default";
	$in{'sparse'} = "default";
	foreach $key (sort (keys %createopts)) {
		$options{$key} = ($in{$key}) ? quotemeta($in{$key}) : undef;
		if ($options{$key}) { $options{$key} =~ s/\\([.:\-])/$1/g; }
	}
	if ($in{'mountpoint'}) { 
		$options{'mountpoint'} = quotemeta($in{'mountpoint'}); 
		$options{'mountpoint'} =~ s/\\\//\//g;
		$options{'mountpoint'} =~ s/\\([.:\-])/$1/g;
	}
	my $display_vdev = $in{'vdev'};
	if ($in{'vdev'} =~ 'stripe') { delete $in{'vdev'}; } else{ $in{'vdev'} .= " "; }
	my @devs = split(/\0/, $in{'devs'});
	if (!@devs) {
		print "<b>Error: No disks selected. Please go back and select at least one disk.</b><br>";
		print ui_table_end();
		ui_print_footer("create.cgi?create=zpool&xnavigation=1", "Create Pool");
		exit;
	}
	my $q_devs = join(" ", map { quotemeta($_) } @devs);
	my $q_pool = quotemeta($in{'pool'});
	my $q_vdev = quotemeta($in{'vdev'});
	my $q_force = quotemeta($in{'force'});
	$q_pool =~ s/\\([.:\-])/$1/g;
	%poolopts = ( 'version' => quotemeta($in{'version'}) );
	my $cmd = (($config{'pool_properties'} =~ /1/)) ? cmd_create_zpool($q_pool, $q_vdev.$q_devs, \%options, \%poolopts, $q_force) : undef;
	$cmd =~ s/\\(\/)/$1/g;
	if ($in{'dryrun'}) {
		# Calculate estimated size
		my $min_bytes = 0;
		my $sum_bytes = 0;
		my $count = 0;
		foreach my $d (@devs) {
			my (undef, undef, undef, $sz) = get_disk_details($d);
			next if $sz eq '-';
			my $b = from_iec($sz);
			if ($count == 0 || $b < $min_bytes) { $min_bytes = $b; }
			$sum_bytes += $b;
			$count++;
		}
		my $est_bytes = 0;
		if ($display_vdev eq 'stripe') { $est_bytes = $sum_bytes; }
		elsif ($display_vdev eq 'mirror') { $est_bytes = $min_bytes; }
		elsif ($display_vdev eq 'raidz1') { $est_bytes = $min_bytes * ($count - 1); }
		elsif ($display_vdev eq 'raidz2') { $est_bytes = $min_bytes * ($count - 2); }
		elsif ($display_vdev eq 'raidz3') { $est_bytes = $min_bytes * ($count - 3); }
		$est_bytes = 0 if $est_bytes < 0;

		print "<b>Dry Run - Configuration:</b><br>";
		print "<ul>";
		print "<li><b>Pool Name:</b> ".&html_escape($in{'pool'})."</li>";
		print "<li><b>Topology:</b> ".&html_escape($display_vdev)."</li>";
		print "<li><b>Estimated Capacity:</b> ".to_iec($est_bytes)."</li>";
		print "<li><b>Disks:</b><ul>";
		foreach my $d (@devs) {
			print "<li>".&html_escape($d)."</li>";
		}
		print "</ul></li>";
		print "</ul>";
		print "<b>Command to be executed:</b><br>";
		print "<pre id='dryrun_cmd'>$cmd</pre>";
		print "<input type='button' value='Copy to Clipboard' onClick='copyToClipboard()'><br><br>";
		print <<EOF;
<script>
function copyToClipboard() {
  var copyText = document.getElementById("dryrun_cmd").innerText;
  var textArea = document.createElement("textarea");
  textArea.value = copyText;
  document.body.appendChild(textArea);
  textArea.select();
  document.execCommand("copy");
  textArea.remove();
  alert("Command copied to clipboard");
}
</script>
EOF
		print ui_table_end();
		ui_print_footer("create.cgi?create=zpool&xnavigation=1", "Create Pool");
		exit;
	}

	$in{'confirm'} = "yes";
	ui_cmd($in{'pool'}, $cmd);
	#print "", (!$result[1]) ? ui_zfs_list($in{'zfs'}) : undef;
	#^^^this doesn't work for some reason
}
elsif ($in{'cmd'} =~ "vdev") {
	$in{'confirm'} = "yes";
	my $q_action = quotemeta($in{'action'});
	my $q_pool = quotemeta($in{'pool'});
	$q_pool =~ s/\\([.:\-])/$1/g;
	my $q_vdev = quotemeta($in{'vdev'});
	my $cmd =  ($config{'pool_properties'} =~ /1/) ? "zpool $q_action $q_pool $q_vdev": undef;
	ui_cmd("$in{'action'} $in{'vdev'}", $cmd);
}
elsif ($in{'cmd'} =~ "promote") {
	print ui_table_end();
	my $q_zfs = quotemeta($in{'zfs'});
	$q_zfs =~ s/\\\//\//g;
	$q_zfs =~ s/\\([.:\-])/$1/g;
	my $cmd = "zfs promote $q_zfs";
	ui_cmd($in{'zfs'}, $cmd);
	print ui_table_start($text{'cmd_title'}, "width=100%", "10", ['align=left'] );
}
elsif ($in{'cmd'} =~ "scrub") {
	$in{'confirm'} = "yes";
	if ($in{'stop'}) { $in{'stop'} = "-s"; }
	my $q_pool = quotemeta($in{'pool'});
	$q_pool =~ s/\\([.:\-])/$1/g;
	my $cmd = "zpool scrub $in{'stop'} $q_pool";
	ui_cmd($in{'pool'}, $cmd);
}
elsif ($in{'cmd'} =~ "upgrade") {
	print "<p>".$text{'zpool_upgrade_msg'}."</p>";
	print ui_table_end();
	my $q_pool = quotemeta($in{'pool'});
	$q_pool =~ s/\\([.:\-])/$1/g;
	my $cmd = "zpool upgrade $q_pool";
	ui_cmd($in{'pool'}, $cmd);
	print ui_table_start($text{'cmd_title'}, "width=100%", "10", ['align=left'] );
}
elsif ($in{'cmd'} =~ "export") {
	print ui_table_end();
	my $q_pool = quotemeta($in{'pool'});
	$q_pool =~ s/\\([.:\-])/$1/g;
	my $q_force = ($in{'force'} && $in{'force'} =~ /-f/) ? "-f " : "";
	if (!$in{'confirm'}) {
		print "Attempting to export pool $in{'pool'} with command... <br />\n";
		print "<i># zpool export $q_pool</i><br /><br />\n";
		print ui_form_start('cmd.cgi', 'post');
		print ui_hidden('cmd', $in{'cmd'});
		print ui_hidden('pool', $in{'pool'});
		print ui_checkbox('force', '-f ', 'Force unmount all datasets before export.', undef), "<br />\n";
		print ui_hidden('confirm', 'yes');
		print "<h3>Would you like to continue?</h3>\n";
		print ui_submit("yes")."<br />";
		print ui_form_end();
	} else {
		my $cmd = "zpool export $q_force$q_pool";
		ui_cmd($in{'pool'}, $cmd);
	}
	print ui_table_start($text{'cmd_title'}, "width=100%", "10", ['align=left'] );
	@footer = ("index.cgi?mode=pools&xnavigation=1", $text{'index_return'});
}
elsif ($in{'cmd'} =~ "import")  {
	my $dir = ();
	if ($in{'dir'}) { 
		my $q_dir = quotemeta($in{'dir'});
		$q_dir =~ s/\\\//\//g;
		$q_dir =~ s/\\([.:\-])/$1/g;
		$dir .= " -d ".$q_dir; 
	}
	if ($in{'destroyed'}) { $dir .= " -D -f "; }
	print ui_table_end();
	my $q_import = quotemeta($in{'import'});
	$q_import =~ s/^\s+|\s+$//g;
	$q_import =~ s/\\([.:\-])/$1/g;
	my $q_force = ($in{'force'} && $in{'force'} =~ /-f/) ? "-f " : "";
	if (!$in{'confirm'}) {
		print "Attempting to import pool $in{'import'} with command... <br />\n";
		print "<i># zpool import".$dir." ".$q_import."</i><br /><br />\n";
		print ui_form_start('cmd.cgi', 'post');
		print ui_hidden('cmd', $in{'cmd'});
		print ui_hidden('import', $in{'import'});
		print ui_hidden('dir', $in{'dir'});
		print ui_hidden('destroyed', $in{'destroyed'});
		print ui_checkbox('force', '-f ', 'Force import even if the pool appears to be in use.', undef), "<br />\n";
		print ui_hidden('confirm', 'yes');
		print "<h3>Would you like to continue?</h3>\n";
		print ui_submit("yes")."<br />";
		print ui_form_end();
	} else {
		my $cmd = ($config{'pool_properties'} =~ /1/ ) ? "zpool import".$dir." ".$q_force.$q_import: undef;
		ui_cmd($in{'import'}, $cmd);
	}
	print ui_table_start($text{'cmd_title'}, "width=100%", "10", ['align=left'] );
	@footer = ("index.cgi?mode=pools&xnavigation=1", $text{'index_return'});
}
elsif ($in{'cmd'} =~ "zfsact")  {
	print ui_table_end();
	my $q_action = quotemeta($in{'action'});
	my $q_zfs = quotemeta($in{'zfs'});
	$q_zfs =~ s/\\\//\//g;
	$q_zfs =~ s/\\([.:\-])/$1/g;
	my $cmd = "zfs $q_action $q_zfs";
	ui_cmd("$in{'action'} $in{'zfs'}", $cmd);
	print ui_table_start($text{'cmd_title'}, "width=100%", "10", ['align=left'] );
}
elsif ($in{'cmd'} =~ "zfsdestroy")  {
	my $q_force = ($in{'force'} && $in{'force'} =~ /-r/) ? "-r " : "";
	my $q_force_unmount = ($in{'force_unmount'} && $in{'force_unmount'} =~ /-f/) ? "-f " : "";
	my $q_zfs = quotemeta($in{'zfs'});
	$q_zfs =~ s/\\\//\//g;
	$q_zfs =~ s/\\([.:\-])/$1/g;
	my $cmd = "zfs destroy $q_force_unmount$q_force$q_zfs";
	ui_cmd($in{'zfs'}, $cmd, 60);
	@footer = ("index.cgi?mode=zfs&xnavigation=1", $text{'zfs_return'});
}
elsif ($in{'cmd'} =~ "snpdestroy")  {
	# On FreeBSD, destroy snapshots with -R to remove dependent clones
	my $freebsd = ($^O eq 'freebsd') ? 1 : 0;
	my $recurse_flag = $freebsd ? '-R ' : '';
	my $q_force = ($in{'force'} && $in{'force'} =~ /-r/) ? "-r " : "";
	my $q_snap = quotemeta($in{'snapshot'});
	$q_snap =~ s/\\\//\//g;
	$q_snap =~ s/\\@/@/g;
	$q_snap =~ s/\\([.:\-])/$1/g;
	my $cmd = "zfs destroy ${recurse_flag}$q_force$q_snap";
	if ($in{'confirm'} ne 'yes')
	{
		print $text{'cmd_destroy'}." $in{'snapshot'}...<br />";
		print "<i># $cmd</i><br /><br />\n";
		print ui_form_start('cmd.cgi', 'post');
		print ui_hidden('cmd', 'snpdestroy');
		print ui_hidden('snapshot', $in{'snapshot'});
		print ui_hidden('submitted', '1');
		print "<b>$text{'cmd_affect'} </b><br />";
		ui_list_snapshots('-r '.$in{'snapshot'});
		if (($config{'zfs_destroy'} =~ /1/) && ($config{'snap_destroy'} =~ /1/)) { print ui_checkbox('force', '-r', 'Click to destroy all child dependencies (recursive)', undef ), "<br />"; }
		print "<h3>$text{'cmd_warning'}</h3>";
		print ui_checkbox('confirm', 'yes', $text{'cmd_understand'}, undef );
		if ($in{'submitted'} && $in{'confirm'} ne 'yes') { print " <font color='red'> -- $text{'cmd_checkbox'}</font>"; }
		print "<br /><br />";
		print ui_submit($text{'continue'}, undef, undef);
		print ui_form_end();

	} else {
		ui_cmd($in{'snapshot'}, $cmd, 60);
	}
	%parent = find_parent($in{'snapshot'});
	@footer = ("status.cgi?zfs=".$parent{'filesystem'}."&xnavigation=1", $parent{'filesystem'});
}
elsif ($in{'cmd'} =~ "pooldestroy")  {
	my $q_pool = quotemeta($in{'pool'});
	$q_pool =~ s/\\([.:\-])/$1/g;
	my $cmd = "zpool destroy $q_pool";
	print ui_table_end();
	ui_cmd($in{'pool'}, $cmd, 60);
	print ui_table_start($text{'cmd_title'}, "width=100%", "10", ['align=left'] );
	@footer = ("index.cgi?mode=pools&xnavigation=1", $text{'index_return'});
}
elsif ($in{'cmd'} =~ "multisnap")  {
	%snapshot = ();
	@select = split(/;/, $in{'select'});
	print "<h2>$text{'destroy'}</h2>";
	print $text{'cmd_multisnap'}." <br />";
	my %results = ();
	print ui_columns_start([ "Snapshot", "Used", "Refer" ]);
	foreach $key (@select)
	{
		$key =~ s/.*[^[:print:]]+//;
		my %snapshot = list_snapshots($key);
		print ui_columns_row([ $key, $snapshot{'00000'}{used}, $snapshot{'00000'}{refer} ]);
		#print Dumper(\%snapshot);
		# On FreeBSD, include -R to destroy snapshots with dependent clones
		my $freebsd = ($^O eq 'freebsd') ? 1 : 0;
		my $recurse_flag = $freebsd ? '-R ' : '';
		my $q_key = quotemeta($key);
		$q_key =~ s/\\\//\//g;
		$q_key =~ s/\\@/@/g;
		$q_key =~ s/\\([.:\-])/$1/g;
		$results{$key} = "zfs destroy ${recurse_flag}$q_key"; 
	}
	print ui_columns_end();
	if (!$in{'confirm'})
	{
		print ui_form_start('cmd.cgi', 'post');
		print ui_hidden('cmd', 'multisnap');
		print ui_hidden('select', $in{'select'});
		print "<h2>$text{'cmd_issue'}</h2>";
		foreach $key (keys %results)
		{
			print $results{$key}, "<br />";
		}	
		print "<h3>$text{'cmd_warning'}</h3>";
		print ui_checkbox('confirm', 'yes', $text{'cmd_understand'}, undef );
		print ui_hidden('checked', 'no');
		if ($in{'checked'} =~ /no/) { print " <font color='red'> -- $text{'cmd_checkbox'}</font>"; }
		print "<br /><br />";
		print ui_submit($text{'continue'}, undef, undef), " | <a href='index.cgi?mode=snapshot&xnavigation=1'>Cancel</a>";
		print ui_form_end();
	} else {
		print "<h2>$text{'cmd_results'}</h2>";
		foreach $key (keys %results)
		{
		my @result = (`$results{$key} 2>&1`);
			if (($result[1] eq undef))
			{
				print $results{$key}, "<br />";
				print "$text{'cmd_success'} <br />";
			} else
			{
				print $results{$key}, "<br />";
				print "$text{'cmd_error'} ", $result[0], "<br />";
			}
		}
	}
	@footer = ('index.cgi?xnavigation=1', $text{'index_return'});
}
elsif ($in{'cmd'} =~ "replace") {
	#$in{'confirm'} = "yes";
	if ($in{'new'}) {
		my $q_pool = quotemeta($in{'pool'});
		$q_pool =~ s/\\([.:\-])/$1/g;
		my $q_vdev = quotemeta($in{'vdev'});
		$q_vdev =~ s/\\([.:\-])/$1/g;
		my $q_new = quotemeta($in{'new'});
		$q_new =~ s/\\([.:\-])/$1/g;
		my $cmd =  ($config{'pool_properties'} =~ /1/) ? "zpool replace $q_pool $q_vdev $q_new": undef;
		print ui_hidden("new", $in{'new'});
		ui_cmd("replace $in{'vdev'} on $in{'pool'} with $in{'new'}", $cmd);
	} else {
		print "Replace $in{'vdev'} on $in{'pool'}: <br />";
		print ui_form_start('cmd.cgi', 'post');
		print ui_hidden("cmd", 'replace');
		print ui_hidden("vdev", $in{'vdev'});
		print ui_hidden("pool", $in{'pool'});
		print "New device: ".ui_filebox("new", "/dev/disk/by-id/")." ".ui_submit('Select');
		print ui_form_end();
	}
}

print ui_table_end();
if (@footer) { ui_print_footer(@footer); }
if ($in{'zfs'} && !@footer) {
		print "<br />";
		ui_print_footer("status.cgi?zfs=".$in{'zfs'}."&xnavigation=1", $in{'zfs'});
} elsif ($in{'pool'} && !@footer) {
		print "<br />";
		ui_print_footer("status.cgi?pool=".$in{'pool'}."&xnavigation=1", $in{'pool'});
} elsif ($in{'snap'} && !@footer) {
		print "<br />";
		ui_print_footer("status.cgi?snap=".$in{'snap'}."&xnavigation=1", $in{'snap'});
}
