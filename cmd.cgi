#!/usr/bin/env perl

require './zfsmanager-lib.pl';
ReadParse();

my %allowed_cmd = map { $_ => 1 } qw(
	setzfs setpool snapshot send createzfs clone rename createzpool
	vdev promote scrub upgrade export import zfsact zfsdestroy
	snpdestroy pooldestroy multisnap replace
);
my %vdev_actions = map { $_ => 1 } qw(offline online remove detach clear);
my %zfs_actions = map { $_ => 1 } qw(mount unmount load-key);
my %cmd_acl = (
	'setzfs'     => 'uzfs_properties',
	'setpool'    => 'upool_properties',
	'snapshot'   => 'uzfs_properties',
	'send'       => 'uzfs_properties',
	'createzfs'  => 'uzfs_properties',
	'clone'      => 'uzfs_properties',
	'rename'     => 'uzfs_properties',
	'createzpool'=> 'upool_properties',
	'vdev'       => 'upool_properties',
	'promote'    => 'uzfs_properties',
	'scrub'      => 'upool_properties',
	'upgrade'    => 'upool_properties',
	'export'     => 'upool_properties',
	'import'     => 'upool_properties',
	'zfsact'     => 'uzfs_properties',
	'zfsdestroy' => 'uzfs_destroy',
	'snpdestroy' => 'usnap_destroy',
	'pooldestroy'=> 'upool_destroy',
	'multisnap'  => 'usnap_destroy',
	'replace'    => 'upool_properties',
);

if (!$in{'cmd'} || !$allowed_cmd{$in{'cmd'}}) {
	error($text{'error_invalid_cmd'} || "Invalid command");
}
require_post_csrf("Command execution");
require_acl_permission($cmd_acl{$in{'cmd'}}, "Access denied for command: ".$in{'cmd'});

if ($in{'pool'} && !is_valid_pool_name($in{'pool'})) { error($text{'error_invalid_pool'} || "Invalid pool name"); }
if ($in{'zfs'} && !is_valid_zfs_name($in{'zfs'})) { error($text{'error_invalid_zfs'} || "Invalid filesystem name"); }
if ($in{'snap'} && $in{'cmd'} ne 'snapshot' && !is_valid_zfs_name($in{'snap'})) { error($text{'error_invalid_snap'} || "Invalid snapshot name"); }
if ($in{'snapshot'} && !is_valid_zfs_name($in{'snapshot'})) { error($text{'error_invalid_snap'} || "Invalid snapshot name"); }
if ($in{'clone'} && !is_valid_zfs_name($in{'clone'})) { error("Invalid clone source"); }
if ($in{'parent'} && !is_valid_zfs_name($in{'parent'}) && !is_valid_pool_name($in{'parent'})) { error("Invalid parent name"); }
if ($in{'property'} && !is_valid_property_name($in{'property'})) { error($text{'error_invalid_property'} || "Invalid property name"); }
if ($in{'vdev'} && !is_valid_vdev_name($in{'vdev'})) { error("Invalid virtual device name"); }
if ($in{'new'} && !is_valid_vdev_name($in{'new'})) { error("Invalid replacement device"); }
if ($in{'action'} && !is_valid_action_name($in{'action'})) { error("Invalid action"); }
if ($in{'name'} && $in{'name'} !~ /^[a-zA-Z0-9_\-.:]+$/) { error("Invalid name"); }
if ($in{'file'} && $in{'file'} !~ /^[a-zA-Z0-9._-]+$/) { error("Invalid filename"); }
if ($in{'dest'} && ($in{'dest'} !~ m{^/} || $in{'dest'} =~ /[\r\n\0]/)) { error("Invalid destination path"); }
if ($in{'dir'} && $in{'dir'} =~ /[\r\n\0]/) { error("Invalid import path"); }
if ($in{'cmd'} eq 'vdev' && !$vdev_actions{$in{'action'}}) { error("Invalid vdev action"); }
if ($in{'cmd'} eq 'zfsact' && !$zfs_actions{$in{'action'}}) { error("Invalid zfs action"); }
if ($in{'cmd'} eq 'createzpool' && $in{'vdev'} && $in{'vdev'} !~ /^(stripe|mirror|raidz1|raidz2|raidz3)$/) { error("Invalid vdev type"); }
if ($in{'cmd'} eq 'scrub' && $in{'stop'} && $in{'stop'} ne 'y') { error("Invalid scrub option"); }
if ($in{'cmd'} eq 'import' && $in{'import'} && $in{'import'} !~ /^[a-zA-Z0-9._:-]+$/) { error("Invalid import target"); }
if ($in{'cmd'} eq 'snapshot' && $in{'snap'} && $in{'snap'} !~ /^[a-zA-Z0-9._:-]+$/) { error("Invalid snapshot name"); }
if ($in{'cmd'} eq 'send' && $in{'snap'} && index($in{'snap'}, '@') == -1) { error("Invalid snapshot name"); }
if ($in{'cmd'} eq 'snpdestroy' && $in{'snapshot'} && index($in{'snapshot'}, '@') == -1) { error("Invalid snapshot name"); }
if (($in{'cmd'} eq 'createzfs' || $in{'cmd'} eq 'clone' || $in{'cmd'} eq 'rename') && $in{'name'} && $in{'name'} !~ /^[a-zA-Z0-9_\-.:]+$/) { error("Invalid dataset name"); }
if (($in{'cmd'} eq 'createzfs' || $in{'cmd'} eq 'clone') && $in{'zfs'} && $in{'zfs'} !~ /^[a-zA-Z0-9_\-.:]+$/) { error("Invalid dataset name"); }

if ($in{'cmd'} eq 'setzfs' && (!$in{'zfs'} || !$in{'property'})) { error("Missing zfs/property"); }
if ($in{'cmd'} eq 'setpool' && (!$in{'pool'} || !$in{'property'})) { error("Missing pool/property"); }
if ($in{'cmd'} eq 'snapshot' && (!$in{'zfs'} || !$in{'snap'})) { error("Missing snapshot parameters"); }
if ($in{'cmd'} eq 'send' && !$in{'snap'}) { error("Missing snapshot"); }
if ($in{'cmd'} eq 'createzfs' && (!$in{'parent'} || !$in{'zfs'})) { error("Missing dataset parameters"); }
if ($in{'cmd'} eq 'clone' && (!$in{'clone'} || !$in{'parent'} || !$in{'zfs'})) { error("Missing clone parameters"); }
if ($in{'cmd'} eq 'rename' && (!$in{'zfs'} || !$in{'parent'} || !$in{'name'})) { error("Missing rename parameters"); }
if ($in{'cmd'} eq 'createzpool' && (!$in{'pool'} || !$in{'devs'})) { error("Missing pool creation parameters"); }
if ($in{'cmd'} eq 'vdev' && (!$in{'pool'} || !$in{'vdev'} || !$in{'action'})) { error("Missing vdev parameters"); }
if ($in{'cmd'} eq 'promote' && !$in{'zfs'}) { error("Missing filesystem"); }
if (($in{'cmd'} eq 'scrub' || $in{'cmd'} eq 'upgrade' || $in{'cmd'} eq 'export' || $in{'cmd'} eq 'pooldestroy') && !$in{'pool'}) { error("Missing pool"); }
if ($in{'cmd'} eq 'import' && !$in{'import'}) { error("Missing import target"); }
if (($in{'cmd'} eq 'zfsact' || $in{'cmd'} eq 'zfsdestroy') && !$in{'zfs'}) { error("Missing filesystem"); }
if ($in{'cmd'} eq 'snpdestroy' && !$in{'snapshot'}) { error("Missing snapshot"); }
if ($in{'cmd'} eq 'multisnap' && !$in{'select'}) { error("Missing snapshot selection"); }
if ($in{'cmd'} eq 'replace' && (!$in{'pool'} || !$in{'vdev'})) { error("Missing replace parameters"); }

ui_print_header(undef, $text{'cmd_title'}, "", undef, 1, 0);

if ($text{$in{'cmd'}."_desc"}) { 
	print ui_table_start($text{$in{'cmd'}."_cmd"}, "width=100%", "10", ['align=left'] );
	print ui_table_row($text{'cmd_dscpt'}, $text{$in{'cmd'}."_desc"});
	print ui_table_end();
};

print ui_table_start($text{'cmd_title'}, "width=100%", "10", ['align=left'] );
	
if ($in{'cmd'} eq "setzfs") {
	$in{'confirm'} = "yes";
	my $prop = $in{'property'};
	my $set = $in{'set'};
	my $zfs = $in{'zfs'};
	if (($in{'set'} =~ "inherit") && ($config{'zfs_properties'} =~ /1/)) { $cmd = "zfs inherit ".shell_quote($prop)." ".shell_quote($zfs); 
	} elsif ($config{'zfs_properties'} =~ /1/) { $cmd =  "zfs set ".shell_quote($prop."=".$set)." ".shell_quote($zfs); }
	ui_cmd("$in{'property'} to $in{'set'} on $in{'zfs'}", $cmd);
}
elsif ($in{'cmd'} eq "setpool")  {
	$in{'confirm'} = "yes";
	my $prop = $in{'property'};
	my $set = $in{'set'};
	my $pool = $in{'pool'};
	my $cmd = ($config{'pool_properties'} =~ /1/) ? "zpool set ".shell_quote($prop."=".$set)." ".shell_quote($pool): undef;
	ui_cmd("$in{'property'} to $in{'set'} in $in{'pool'}", $cmd);
}
elsif ($in{'cmd'} eq "snapshot")  {
	my $target = $in{'zfs'}."@".$in{'snap'};
	my $cmd = "zfs snapshot ".shell_quote($target);
	$in{'confirm'} = "yes";
	ui_cmd($in{'snap'}, $cmd);
}
elsif ($in{'cmd'} eq "send") {
	if (!$in{'dest'}) {
                print $text{'cmd_send'}." ".h($in{'snap'})." ".$text{'cmd_gzip'}."  <br />";
                print "<br />";
                print ui_form_start('cmd.cgi', 'post');
                print ui_csrf_hidden();
                print ui_hidden('cmd', $in{'cmd'});
		print ui_hidden('snap', $in{'snap'});
		my $newfile = $in{'snap'} =~ s![/@]!_!gr;
		print "<b>$text{'destination'} </b>".ui_filebox('dest', $config{'last_send'}, 35, undef, undef, undef, 1)."<br />";
		print "<b>$text{'filename'} </b>".ui_textbox('file', $newfile.'.gz', 50)."<br />";
		print "<input type='submit' name='continue_btn' id='continue_btn' value=\"".quote_escape($text{'continue'})."\">";
                print ui_form_end();
	} else { 
		$in{'confirm'} = "yes";
		my $snap = $in{'snap'};
		my $dest = $in{'dest'};
		my $file = $in{'file'};
		my $target_path = $dest."/".$file;
		my $q_target = quote_path($target_path);
		my $cmd = "zfs send ".shell_quote($snap)." | gzip > ".$q_target;
		ui_cmd($in{'snap'}, $cmd);
		$config{'last_send'} = $in{'dest'};
		save_module_config();
		my $list_cmd = "ls -al ".$q_target." 2>&1";
		my $listing = `$list_cmd`;
		print "<pre>".h($listing)."</pre>";
	}
}
elsif ($in{'cmd'} eq "createzfs")  {
	my %createopts = create_opts();
	my %options = ();
	foreach $key (sort (keys %createopts)) {
		$options{$key} = ($in{$key}) ? $in{$key} : undef;
	}
	if ($in{'mountpoint'}) { 
		$options{'mountpoint'} = $in{'mountpoint'}; 
	}
	if ($in{'zvol'} == '1') { 
		$options{'zvol'} = $in{'size'};
		$options{'sparse'} = $in{'sparse'};
		$options{'volblocksize'} = $in{'volblocksize'};
		foreach my $k ('logbias', 'primarycache', 'secondarycache', 'refreservation') {
			if ($in{$k}) { 
				$options{$k} = $in{$k};
			}
		}
	} 
	my $parent = $in{'parent'};
	my $zfs = $in{'zfs'};
	my $cmd = ($in{'parent'}) ? cmd_create_zfs($parent."/".$zfs, \%options) : undef;
	if ($in{'add_inherit'} && $cmd) {
		my $acl_cmd = acl_inherit_flags_cmd($parent."/".$zfs);
		if ($acl_cmd) { $cmd .= " && ".$acl_cmd; }
	}
	if ($in{'add_inherit'}) {
		my @missing = acl_inherit_missing_tools();
		if (@missing) {
			print "<b>Warning:</b> ACL inherit flags requested, but missing tool(s) in PATH: ".h(join(", ", @missing)).". Flags will not be set.<br />\n";
		}
	}
	$in{'confirm'} = "yes";
	ui_cmd("$in{'parent'}/$in{'zfs'}", $cmd);
	#print "", (!$result[1]) ? ui_zfs_list($in{'zfs'}) : undef;
	#^^^this doesn't work for some reason
	@footer = ("status.cgi?zfs=".u($in{'parent'}."/".$in{'zfs'})."&xnavigation=1", h($in{'parent'}."/".$in{'zfs'}));
}
elsif ($in{'cmd'} eq "clone")  {
	my %createopts = create_opts();
	$opts = "";
	foreach $key (sort (keys %createopts))
	{
		if ($in{$key})
		{
			my $val = $in{$key};
			$opts = ($in{$key} =~ 'default') ? $opts : $opts.' -o '.shell_quote($key.'='.$val);
		}
	}
	if ($in{'mountpoint'}) { 
		my $mp = $in{'mountpoint'};
		$opts .= ' -o '.shell_quote('mountpoint='.$mp); 
	}
	$in{'confirm'} = "yes";
	my $clone = $in{'clone'};
	my $parent = $in{'parent'};
	my $zfs = $in{'zfs'};
	my $cmd = "zfs clone ".shell_quote($clone)." ".shell_quote($parent.'/'.$zfs)." ".$opts;
	if ($in{'add_inherit'} && $cmd) {
		my $acl_cmd = acl_inherit_flags_cmd($parent."/".$zfs);
		if ($acl_cmd) { $cmd .= " && ".$acl_cmd; }
	}
	if ($in{'add_inherit'}) {
		my @missing = acl_inherit_missing_tools();
		if (@missing) {
			print "<b>Warning:</b> ACL inherit flags requested, but missing tool(s) in PATH: ".h(join(", ", @missing)).". Flags will not be set.<br />\n";
		}
	}
	ui_cmd($in{'clone'}, $cmd);
	@footer = ("status.cgi?snap=".u($in{'clone'})."&xnavigation=1", h($in{'clone'}))
}
elsif ($in{'cmd'} eq "rename")  {
	my $q_zfs = shell_quote($in{'zfs'});
	my $q_force = ($in{'force'} && $in{'force'} =~ /-f/) ? "-f " : "";
	my $q_recurse = ($in{'recurse'} && $in{'recurse'} =~ /-r/) ? "-r " : "";
	my $q_prnt = ($in{'prnt'} && $in{'prnt'} =~ /-p/) ? "-p " : "";
	if (index($in{'zfs'}, '@') != -1) { 
		my $target = $in{'parent'}.'@'.$in{'name'};
		$cmd = "zfs rename ".$q_force.$q_recurse.$q_zfs." ".shell_quote($target);
		@footer = ('status.cgi?snap='.u($target).'&xnavigation=1', h($target));
	} elsif (index($in{'zfs'}, '/') != -1) { 
		my $target = $in{'parent'}.'/'.$in{'name'};
		$cmd = "zfs rename ".$q_force.$q_prnt.$q_zfs." ".shell_quote($target);
		if ($in{'confirm'}) { @footer = ('status.cgi?zfs='.u($target).'&xnavigation=1', h($target)); }
	}
	print ui_table_end();
	ui_cmd($in{'zfs'}." to ".$in{'name'}, $cmd);
	print ui_table_start($text{'cmd_title'}, "width=100%", "10", ['align=left'] );
}
elsif ($in{'cmd'} eq "createzpool")  {
	my %createopts = create_opts();
	my %options = ();
	$in{'volblocksize'} = "default";
	$in{'sparse'} = "default";
	foreach $key (sort (keys %createopts)) {
		$options{$key} = ($in{$key}) ? $in{$key} : undef;
	}
	if ($in{'mountpoint'}) { 
		$options{'mountpoint'} = $in{'mountpoint'}; 
	}
	my $display_vdev = $in{'vdev'};
	my $vdev = $in{'vdev'};
	if ($vdev =~ 'stripe') { $vdev = ''; }
	my @devs = split(/\0/, $in{'devs'});
	foreach my $d (@devs) {
		if (!is_valid_vdev_name($d)) { error("Invalid device name: ".h($d)); }
	}
	if (!@devs) {
		print "<b>Error: No disks selected. Please go back and select at least one disk.</b><br>";
		print ui_table_end();
		ui_print_footer("create.cgi?create=zpool&xnavigation=1", "Create Pool");
		exit;
	}
	my $force = ($in{'force'} && $in{'force'} =~ /-f/) ? "-f" : "";
	%poolopts = ( 'version' => $in{'version'} );
	my $cmd = (($config{'pool_properties'} =~ /1/)) ? cmd_create_zpool($in{'pool'}, $vdev, \@devs, \%options, \%poolopts, $force) : undef;
	if ($in{'add_inherit'} && $cmd) {
		my $acl_cmd = acl_inherit_flags_cmd($in{'pool'});
		if ($acl_cmd) { $cmd .= " && ".$acl_cmd; }
	}
	if ($in{'add_inherit'}) {
		my @missing = acl_inherit_missing_tools();
		if (@missing) {
			print "<b>Warning:</b> ACL inherit flags requested, but missing tool(s) in PATH: ".h(join(", ", @missing)).". Flags will not be set.<br />\n";
		}
	}
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
		print "<li><b>Pool Name:</b> ".h($in{'pool'})."</li>";
		print "<li><b>Topology:</b> ".h($display_vdev)."</li>";
		print "<li><b>Estimated Capacity:</b> ".to_iec($est_bytes)."</li>";
		print "<li><b>Disks:</b><ul>";
		foreach my $d (@devs) {
			print "<li>".h($d)."</li>";
		}
		print "</ul></li>";
		print "</ul>";
		print "<b>Command to be executed:</b><br>";
		print "<pre id='dryrun_cmd'>".h($cmd)."</pre>";
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
elsif ($in{'cmd'} eq "vdev") {
	$in{'confirm'} = "yes";
	my $cmd =  ($config{'pool_properties'} =~ /1/) ? "zpool ".shell_quote($in{'action'})." ".shell_quote($in{'pool'})." ".shell_quote($in{'vdev'}): undef;
	ui_cmd("$in{'action'} $in{'vdev'}", $cmd);
}
elsif ($in{'cmd'} eq "promote") {
	print ui_table_end();
	my $cmd = "zfs promote ".shell_quote($in{'zfs'});
	ui_cmd($in{'zfs'}, $cmd);
	print ui_table_start($text{'cmd_title'}, "width=100%", "10", ['align=left'] );
}
elsif ($in{'cmd'} eq "scrub") {
	$in{'confirm'} = "yes";
	if ($in{'stop'}) { $in{'stop'} = "-s"; }
	my $cmd = "zpool scrub $in{'stop'} ".shell_quote($in{'pool'});
	ui_cmd($in{'pool'}, $cmd);
}
elsif ($in{'cmd'} eq "upgrade") {
	print "<p>".$text{'zpool_upgrade_msg'}."</p>";
	print ui_table_end();
	my $cmd = "zpool upgrade ".shell_quote($in{'pool'});
	ui_cmd($in{'pool'}, $cmd);
	print ui_table_start($text{'cmd_title'}, "width=100%", "10", ['align=left'] );
}
elsif ($in{'cmd'} eq "export") {
	print ui_table_end();
	my $q_pool = shell_quote($in{'pool'});
	my $q_force = ($in{'force'} && $in{'force'} =~ /-f/) ? "-f " : "";
	if (!$in{'confirm'}) {
		print "Attempting to export pool ".h($in{'pool'})." with command... <br />\n";
		print "<i># ".h("zpool export $q_pool")."</i><br /><br />\n";
		print ui_form_start('cmd.cgi', 'post');
		print ui_csrf_hidden();
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
elsif ($in{'cmd'} eq "import")  {
	my $dir = "";
	if ($in{'dir'}) { 
		$dir .= " -d ".shell_quote($in{'dir'}); 
	}
	if ($in{'destroyed'}) { $dir .= " -D -f "; }
	print ui_table_end();
	my $import = $in{'import'};
	$import =~ s/^\s+|\s+$//g;
	my $q_force = ($in{'force'} && $in{'force'} =~ /-f/) ? "-f " : "";
	if (!$in{'confirm'}) {
		print "Attempting to import pool ".h($in{'import'})." with command... <br />\n";
		print "<i># ".h("zpool import".$dir." ".shell_quote($import))."</i><br /><br />\n";
		print ui_form_start('cmd.cgi', 'post');
		print ui_csrf_hidden();
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
		my $cmd = ($config{'pool_properties'} =~ /1/ ) ? "zpool import".$dir." ".$q_force.shell_quote($import): undef;
		ui_cmd($in{'import'}, $cmd);
	}
	print ui_table_start($text{'cmd_title'}, "width=100%", "10", ['align=left'] );
	@footer = ("index.cgi?mode=pools&xnavigation=1", $text{'index_return'});
}
elsif ($in{'cmd'} eq "zfsact")  {
	print ui_table_end();
	my $cmd = "zfs ".shell_quote($in{'action'})." ".shell_quote($in{'zfs'});
	ui_cmd("$in{'action'} $in{'zfs'}", $cmd);
	print ui_table_start($text{'cmd_title'}, "width=100%", "10", ['align=left'] );
}
elsif ($in{'cmd'} eq "zfsdestroy")  {
	my $q_force = ($in{'force'} && $in{'force'} =~ /-r/) ? "-r " : "";
	my $q_force_unmount = ($in{'force_unmount'} && $in{'force_unmount'} =~ /-f/) ? "-f " : "";
	my $cmd = "zfs destroy $q_force_unmount$q_force".shell_quote($in{'zfs'});
	ui_cmd($in{'zfs'}, $cmd, 60);
	@footer = ("index.cgi?mode=zfs&xnavigation=1", $text{'zfs_return'});
}
elsif ($in{'cmd'} eq "snpdestroy")  {
	# On FreeBSD, destroy snapshots with -R to remove dependent clones
	my $freebsd = ($^O eq 'freebsd') ? 1 : 0;
	my $recurse_flag = $freebsd ? '-R ' : '';
	my $q_force = ($in{'force'} && $in{'force'} =~ /-r/) ? "-r " : "";
	my $cmd = "zfs destroy ${recurse_flag}$q_force".shell_quote($in{'snapshot'});
	if ($in{'confirm'} ne 'yes')
	{
		print $text{'cmd_destroy'}." ".h($in{'snapshot'})."...<br />";
		print "<i># ".h($cmd)."</i><br /><br />\n";
		print ui_form_start('cmd.cgi', 'post');
		print ui_csrf_hidden();
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
		print "<input type='submit' name='continue_btn' id='continue_btn' value=\"".quote_escape($text{'continue'})."\">";
		print ui_form_end();

	} else {
		ui_cmd($in{'snapshot'}, $cmd, 60);
	}
	%parent = find_parent($in{'snapshot'});
	@footer = ("status.cgi?zfs=".u($parent{'filesystem'})."&xnavigation=1", h($parent{'filesystem'}));
}
elsif ($in{'cmd'} eq "pooldestroy")  {
	my $q_force = ($in{'force'} && $in{'force'} =~ /-f/) ? "-f " : "";
	my $q_pool = shell_quote($in{'pool'});
	my $cmd = "zpool destroy $q_force$q_pool";
	print ui_table_end();
	ui_cmd($in{'pool'}, $cmd, 60);
	print ui_table_start($text{'cmd_title'}, "width=100%", "10", ['align=left'] );
	@footer = ("index.cgi?mode=pools&xnavigation=1", $text{'index_return'});
}
elsif ($in{'cmd'} eq "multisnap")  {
	%snapshot = ();
	my @select = ();
	my %seen = ();
	foreach my $chunk (split(/\0/, ($in{'select'} || ''))) {
		foreach my $entry (split(/;/, $chunk)) {
			$entry =~ s/^\s+|\s+$//g;
			next if ($entry eq '');
			next if ($seen{$entry}++);
			push(@select, $entry);
		}
	}
	if (!@select) {
		error("Invalid snapshot entry in selection");
	}
	my $select_payload = join(";", @select);
	$select_payload .= ";" if ($select_payload ne "");
	print "<h2>$text{'destroy'}</h2>";
	print $text{'cmd_multisnap'}." <br />";
	my %results = ();
	print ui_columns_start([ "Snapshot", "Used", "Refer" ]);
	foreach my $key (@select)
	{
		if (!is_valid_zfs_name($key) || index($key, '@') == -1) {
			error("Invalid snapshot entry in selection");
		}
		my %snapshot = list_snapshots($key);
		if (!%snapshot) {
			error("Invalid snapshot entry in selection");
		}
		print ui_columns_row([ h($key), h($snapshot{'00000'}{used}), h($snapshot{'00000'}{refer}) ]);
		#print Dumper(\%snapshot);
		# On FreeBSD, include -R to destroy snapshots with dependent clones
		my $freebsd = ($^O eq 'freebsd') ? 1 : 0;
		my $recurse_flag = $freebsd ? '-R ' : '';
		$results{$key} = "zfs destroy ${recurse_flag}".shell_quote($key); 
	}
	print ui_columns_end();
	if (!$in{'confirm'})
	{
		print ui_form_start('cmd.cgi', 'post');
		print ui_csrf_hidden();
		print ui_hidden('cmd', 'multisnap');
		print ui_hidden('select', $select_payload);
		print "<h2>$text{'cmd_issue'}</h2>";
		foreach my $key (keys %results)
		{
			print h($results{$key}), "<br />";
		}	
		print "<h3>$text{'cmd_warning'}</h3>";
		print ui_checkbox('confirm', 'yes', $text{'cmd_understand'}, undef );
		print ui_hidden('checked', 'no');
		if ($in{'checked'} =~ /no/) { print " <font color='red'> -- $text{'cmd_checkbox'}</font>"; }
		print "<br /><br />";
		print "<input type='submit' name='continue_btn' id='continue_btn' value=\"".quote_escape($text{'continue'})."\"> ";
		print "<input type='button' name='cancel_btn' id='cancel_btn' value='Cancel' onclick=\"window.location.href='index.cgi?mode=snapshot&xnavigation=1'; return false;\">";
		print ui_form_end();
	} else {
		print "<h2>$text{'cmd_results'}</h2>";
		foreach my $key (keys %results)
		{
		my @result = (`$results{$key} 2>&1`);
			if (($result[1] eq undef))
			{
				print h($results{$key}), "<br />";
				print "$text{'cmd_success'} <br />";
			} else
			{
				print h($results{$key}), "<br />";
				print "$text{'cmd_error'} ", h($result[0]), "<br />";
			}
		}
	}
	@footer = ('index.cgi?xnavigation=1', $text{'index_return'});
}
elsif ($in{'cmd'} eq "replace") {
	#$in{'confirm'} = "yes";
	if ($in{'new'}) {
		my $cmd =  ($config{'pool_properties'} =~ /1/) ? "zpool replace ".shell_quote($in{'pool'})." ".shell_quote($in{'vdev'})." ".shell_quote($in{'new'}): undef;
		print ui_hidden("new", $in{'new'});
		ui_cmd("replace $in{'vdev'} on $in{'pool'} with $in{'new'}", $cmd);
	} else {
		print "Replace ".h($in{'vdev'})." on ".h($in{'pool'}).": <br />";
		print ui_form_start('cmd.cgi', 'post');
		print ui_csrf_hidden();
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
		ui_print_footer("status.cgi?zfs=".u($in{'zfs'})."&xnavigation=1", h($in{'zfs'}));
} elsif ($in{'pool'} && !@footer) {
		print "<br />";
		ui_print_footer("status.cgi?pool=".u($in{'pool'})."&xnavigation=1", h($in{'pool'}));
} elsif ($in{'snap'} && !@footer) {
		print "<br />";
		ui_print_footer("status.cgi?snap=".u($in{'snap'})."&xnavigation=1", h($in{'snap'}));
}
