#!/usr/bin/env perl

require './zfsmanager-lib.pl';
ReadParse();

if ($in{'pool'} && !is_valid_pool_name($in{'pool'})) { error($text{'error_invalid_pool'} || "Invalid pool name"); }
if ($in{'parent'} && !is_valid_zfs_name($in{'parent'}) && !is_valid_pool_name($in{'parent'})) { error("Invalid parent name"); }
if ($in{'zfs'} && !is_valid_zfs_name($in{'zfs'})) { error($text{'error_invalid_zfs'} || "Invalid filesystem name"); }
if ($in{'rename'} && !is_valid_zfs_name($in{'rename'})) { error("Invalid rename target"); }
if ($in{'destroy_zfs'} && !is_valid_zfs_name($in{'destroy_zfs'})) { error("Invalid filesystem name"); }
if ($in{'destroy_pool'} && !is_valid_pool_name($in{'destroy_pool'})) { error("Invalid pool name"); }
if ($in{'clone'} && !is_valid_zfs_name($in{'clone'})) { error("Invalid snapshot name"); }
if ($in{'dir'} && $in{'dir'} =~ /[\r\n\0]/) { error("Invalid directory path"); }

my %createopts = create_opts();
my %proplist = properties_list();
my %fs_descriptions = (
	'recordsize' => {
		'128K' => '128K (General/Default)',
		'1M' => '1M (Media/Large files)',
		'4M' => '4M',
		'16K' => '16K (Database)',
		'4K' => '4K (VM)'
	},
	'compression' => {
		'lz4' => 'lz4 (Recommended)',
		'off' => 'off (None)',
		'gzip' => 'gzip (High compression)'
	},
	'atime' => {
		'off' => 'off (Performance)',
		'on' => 'on (Record access time)'
	},
	'sync' => {
		'disabled' => 'disabled (Performance)',
		'standard' => 'standard (Safety)',
		'always' => 'always (Maximum Safety)'
	},
	'acltype' => {
		'nfsv4' => 'nfsv4 (ZFS Default)',
		'posixacl' => 'posixacl (Linux Default)'
	},
	'aclinherit' => {
		'passthrough' => 'passthrough (SMB Recommended)',
		'restricted' => 'restricted (ZFS Default)'
	},
	'aclmode' => {
		'passthrough' => 'passthrough (SMB Recommended)',
		'discard' => 'discard (ZFS Default)'
	}
);
my @fs_order = ('recordsize', 'compression', 'atime', 'sync', 'exec', 'canmount', 'acltype', 'aclinherit', 'aclmode', 'xattr');
my %acl_tooltips = (
	'acltype' => 'Controls whether ACLs are enabled and if so what type of ACL to use.',
	'aclinherit' => 'Controls how ACL entries are inherited when files and directories are created.',
	'aclmode' => 'Controls how an ACL is modified during a chmod operation.'
);

#create zpool
if ($in{'create'} =~ "zpool")
{
	require_acl_permission('upool_properties', 'Permission denied');
	ui_print_header(undef, "Create Pool", "", undef, 1, 0);
	print ui_form_start("cmd.cgi", "post", undef, "onsubmit='return validatePool(this)'");
	print ui_csrf_hidden();
	print ui_hidden('cmd', 'createzpool');
	print ui_hidden('create', 'zpool');

	# Section 1: Pool Configuration
	print ui_table_start("Pool Configuration", 'width=100%');
	print ui_table_row('Pool Name', ui_textbox('pool', $in{'pool'}, 40));
	print ui_table_row('Mount Point (blank for default)', ui_filebox('mountpoint', $in{'mountpoint'}, 40, undef, undef, 1));
	if (!$in{'version'}) { $in{'version'} = 'default'; }
	print ui_table_row('Pool Version', ui_select('version', $in{'version'}, ['default', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28'], 1, 0, 1));
	print ui_table_row('Force Creation', ui_checkbox('force', '-f', 'Force use of disks, even if they are in use.'));
	print ui_table_end();

	# Section 2: Filesystem Properties
	print ui_table_start("File System Properties", "width=100%", undef);
	foreach $key (@fs_order)
	{
		my @options;
		push(@options, ['default', 'default']);
		my @raw_opts = ($proplist{$key} eq 'boolean') ? ('on', 'off') : split(", ", $proplist{$key});
		foreach my $opt (@raw_opts) {
			my $label = $fs_descriptions{$key}{$opt} || $opt;
			push(@options, [$opt, $label]);
		}
		my $default_val = $createopts{$key} || 'default';
		my %opt_seen = map { $_->[0] => 1 } @options;
		if ($default_val ne 'default' && !$opt_seen{$default_val}) {
			my $label = $fs_descriptions{$key}{$default_val} || $default_val;
			push(@options, [$default_val, $label]);
		}
		my $help = $acl_tooltips{$key} ? "<br><small><i>$acl_tooltips{$key}</i></small>" : "";
		my $selected = defined($in{$key}) ? $in{$key} : $default_val;
		print ui_table_row($key.': ', ui_select($key, $selected, \@options, 1, 0, 1).$help);
	}
	my $add_inherit_default = defined($in{'add_inherit'}) ? $in{'add_inherit'} : 1;
	print ui_table_row('ACL inherit flags:', ui_checkbox('add_inherit', 1, 'Add :fd to base NFSv4 ACL entries', $add_inherit_default));
	print ui_table_end();

	# Section 3: Device Configuration
	print ui_table_start("Device Configuration:", "width=100%", undef);
	if (!$in{'vdev'}) { $in{'vdev'} = 'stripe'; }
	$in{'filter_boot'} = 1 if !defined $in{'filter_boot'};
	$in{'filter_used'} = 1 if !defined $in{'filter_used'};
	my $boot_label = $in{'filter_boot'} ? "Show Boot Disks" : "Hide Boot Disks";
	my $boot_val   = $in{'filter_boot'} ? 0 : 1;
	my $used_label = $in{'filter_used'} ? "Show Used Disks" : "Hide Used Disks";
	my $used_val   = $in{'filter_used'} ? 0 : 1;
	my $filter_used_js = js_escape($in{'filter_used'});
	my $filter_boot_js = js_escape($in{'filter_boot'});
	my $js_boot = "onclick='location.href=\"create.cgi?create=zpool&filter_boot=$boot_val&filter_used=$filter_used_js&xnavigation=1\"; return false;'";
	my $js_used = "onclick='location.href=\"create.cgi?create=zpool&filter_boot=$filter_boot_js&filter_used=$used_val&xnavigation=1\"; return false;'";
	my $filters = "&nbsp;&nbsp;" . ui_button($boot_label, "btn_boot", 0, $js_boot) . "&nbsp;&nbsp;" . ui_button($used_label, "btn_used", 0, $js_used);

	print ui_table_row("VDEV Type", ui_select('vdev', $in{'vdev'}, ['stripe', 'mirror', 'raidz1', 'raidz2', 'raidz3'], 1, 0, 1) . $filters);
	my $disks = list_disk_ids($in{'filter_boot'}, $in{'filter_used'});
	my @disk_opts;
	foreach my $label (sort keys %{$disks->{byid}}) {
		push @disk_opts, [ $disks->{byid}->{$label}, $label ];
	}
	my $max_label_len = 0;
	foreach my $opt (@disk_opts) {
		my $label = $opt->[1];
		$label =~ s/<[^>]*>//g;
		my $len = length($label);
		$max_label_len = $len if ($len > $max_label_len);
	}
	my $select_style = "style='width:100%; min-width:${max_label_len}ch'";
	my @selected_disks = split(/\0|;/, $in{'devs'});
	my %sel_map = map { $_ => 1 } @selected_disks;
	my @avail_opts;
	my @sel_opts_full;
	foreach my $opt (@disk_opts) {
		if ($sel_map{$opt->[0]}) {
			push @sel_opts_full, $opt;
		} else {
			push @avail_opts, $opt;
		}
	}
	print ui_table_row("Disks", 
		"<table width='100%'>
		<tr><td><b>Available</b><br>" .
		ui_select("devs_avail", undef, \@avail_opts, 10, 1, 0, 0, "$select_style onclick='moveDisks(this, this.form.devs)'") . 
		"</td></tr>" .
		"<tr><td><b>Selected</b><br>" .
		ui_select("devs", undef, \@sel_opts_full, 10, 1, 0, 0, "$select_style onclick='moveDisks(this, this.form.devs_avail)'") . 
		"</td></tr></table>"
	);
	print ui_table_end();
	print ui_submit('Create', 'create');
	print "&nbsp;";
	print ui_button('Dry Run', 'dryrun_btn', undef, "onClick='submitDryRun(this.form)'");
	print ui_form_end();
	@footer = ("index.cgi?mode=pools&xnavigation=1", $text{'index_return'});

	# Get existing pools for validation
	my %pools = list_zpools();
	my @pool_names = keys %pools;
	my $pool_list_js = join(",", map { "'".js_escape($_)."'" } @pool_names);

	print <<EOF;
<script type="text/javascript">
function moveDisks(src, dest) {
	for (var i = 0; i < src.options.length; i++) {
		if (src.options[i].selected) {
			var opt = src.options[i];
			var newOpt = new Option(opt.text, opt.value);
			dest.options[dest.options.length] = newOpt;
			src.options[i] = null;
			i--;
		}
	}
}
function validatePool(form, skipConfirm) {
	var name = form.pool.value;
	var nameRegex = /^[a-zA-Z][a-zA-Z0-9_\\-.]*\$/;
	if (!name || !nameRegex.test(name)) {
		alert("Invalid Pool Name. Must start with a letter and contain only alphanumeric characters, -, _, or .");
		return false;
	}
	var existingPools = [$pool_list_js];
	if (existingPools.indexOf(name) !== -1) {
		alert("A pool with name '" + name + "' already exists.");
		return false;
	}
	var devs = form.devs;
	var force = form.force && form.force.checked;
	var usedSelected = false;
	for (var i=0; i<devs.options.length; i++) { devs.options[i].selected = true; }
	var diskSummary = "";
	if (devs && devs.options) {
		if (devs.options.length === 0) {
			alert("Please select at least one disk.");
			return false;
		}
		for (var i = 0; i < devs.options.length; i++) {
			var text = devs.options[i].text;
			if (text.indexOf("color:red") !== -1 || (text.indexOf("[") !== -1 && text.indexOf("]") !== -1 && text.indexOf("[Available]") === -1)) {
				if (force) {
					usedSelected = true;
				} else {
					alert("Selected disk '" + text.replace(/<[^>]*>/g, "") + "' is already in use. Please deselect it.");
					return false;
				}
			}
			diskSummary += "- " + text.replace(/<[^>]*>/g, "") + "\\n";
		}
	}
	if (usedSelected) {
		var warn = "You will DESTROY already used disk(s)! Are you sure!";
		if (!confirm(warn)) {
			return false;
		}
	}
	if (skipConfirm) return true;
	var msg = "About to create pool '" + name + "' with " + devs.options.length + " disk(s):\\n\\n" + diskSummary + "\\nContinue?";
	return confirm(msg);
}
function submitDryRun(form) {
	if (!validatePool(form, true)) return;
	var oldTarget = form.target;
	form.target = "_blank";
	var input = document.createElement("input");
	input.type = "hidden";
	input.name = "dryrun";
	input.value = "1";
	form.appendChild(input);
	form.submit();
	setTimeout(function() {
		form.target = oldTarget;
		form.removeChild(input);
	}, 100);
}
</script>
EOF
#create zfs file system
#TODO the $in{'pool'} variable should be changed to $in{'parent'}, but it still works
} elsif (($in{'create'} =~ "zfs") & ($in{'parent'} eq undef)) {
	require_acl_permission('uzfs_properties', 'Permission denied');
	ui_print_header(undef, "Create File System", "", undef, 1, 0);
	print "<b>Select parent for file system</b>";
	ui_zfs_list(undef, "create.cgi?create=zfs&xnavigation=1&parent=");
	@footer = ('index.cgi?mode=zfs&xnavigation=1', $text{'zfs_return'});
} elsif (($in{'create'} =~ "zfs")) {
	require_acl_permission('uzfs_properties', 'Permission denied');
	ui_print_header(undef, "Create File System", "", undef, 1, 0);
	#Show associated file systems
	
	print "Parent file system:";
	ui_zfs_list($in{'parent'}, "");
	
	@tabs = ();
	push(@tabs, [ "zfs", "Create Filesystem", "create.cgi?mode=zfs&xnavigation=1" ]);
	push(@tabs, [ "zvol", "Create Volume", "create.cgi?mode=zvol&xnavigation=1" ]);
	print &ui_tabs_start(\@tabs, "mode", $in{'mode'} || $tabs[0]->[0], 1);
	
	print &ui_tabs_start_tab("mode", "zfs");
	
	print ui_form_start("cmd.cgi", "post", undef, "onsubmit='return validateFsForm(this)'");
	print ui_csrf_hidden();
	print ui_table_start('New File System', 'width=100%', '2');
	print ui_table_row("Name:", h($in{'parent'})."/".ui_textbox('zfs'));
	print ui_table_row("Mount point:", ui_filebox('mountpoint', '', 25, undef, undef, 1)." (blank for default)");
	print ui_hidden('parent', $in{'parent'});
	print ui_hidden('create', 'zfs');
	print ui_hidden('cmd', 'createzfs');
	print ui_table_row(undef, "<br />");
	print ui_table_end();
	print ui_table_start("File system options", "width=100%", undef);
	foreach $key (@fs_order)
	{
		my @options;
		push(@options, ['default', 'default']);
		my @raw_opts = ($proplist{$key} eq 'boolean') ? ('on', 'off') : split(", ", $proplist{$key});
		foreach my $opt (@raw_opts) {
			my $label = $fs_descriptions{$key}{$opt} || $opt;
			push(@options, [$opt, $label]);
		}
		my $default_val = $createopts{$key} || 'default';
		my %opt_seen = map { $_->[0] => 1 } @options;
		if ($default_val ne 'default' && !$opt_seen{$default_val}) {
			my $label = $fs_descriptions{$key}{$default_val} || $default_val;
			push(@options, [$default_val, $label]);
		}
		my $help = $acl_tooltips{$key} ? "<br><small><i>$acl_tooltips{$key}</i></small>" : "";
		my $selected = defined($in{$key}) ? $in{$key} : $default_val;
		print ui_table_row($key.': ', ui_select($key, $selected, \@options, 1, 0, 1).$help);
	}
	my $add_inherit_default = defined($in{'add_inherit'}) ? $in{'add_inherit'} : 1;
	print ui_table_row('ACL inherit flags:', ui_checkbox('add_inherit', 1, 'Add :fd to base NFSv4 ACL entries', $add_inherit_default));
	print ui_table_end();
	print ui_submit('Create');
	print ui_form_end();
	print &ui_tabs_end_tab("mode", "zfs");

	print &ui_tabs_start_tab("mode", "zvol");
	print ui_form_start("cmd.cgi", "post", undef, "onsubmit='return validateZvolForm(this)'");
	print ui_csrf_hidden();
	print ui_table_start('New Volume', 'width=100%', '2');
	print ui_table_row("Name:", h($in{'parent'})."/".ui_textbox('zfs'));
	print ui_table_row("Size:", ui_textbox('size', undef, 20, undef, undef, "oninput='updateRefres()'"));
	print ui_hidden('parent', $in{'parent'});
	print ui_hidden('create', 'zfs');
	print ui_hidden('cmd', 'createzfs');
	print ui_hidden('zvol', '1');
	print ui_table_row(undef, "<br />");
	print ui_table_end();
	print ui_table_start("Volume options", "width=100%", undef);
	my %zvol_createopts = (
		'volblocksize' => '16K',
		'compression' => 'lz4',
		'sync'        => 'disabled',
		'logbias'     => 'latency',
		'primarycache' => 'all',
		'secondarycache' => 'all',
		'refreservation' => 'none',
	);
	my %zvol_descriptions = (
		'volblocksize' => {
			'512' => '(512B)',
			'1K' => '(1K)',
			'2K' => '(2K)',
			'4K' => '(4K) Swap',
			'8K' => '(8K) Databases',
			'16K' => '16K (VM/Default)',
			'64K' => '64K (Backups)'
		},
		'logbias' => {
			'latency' => 'latency (databases, NFS sync)',
			'throughput' => 'throughput (VM, media/backups)'
		},
		'primarycache' => {
			'all' => 'all (filesystems)',
			'metadata' => 'metadata (VM, iSCSI)',
			'none' => 'none (Swap)'
		},
		'secondarycache' => {
			'all' => 'all (general filesystems)',
			'metadata' => 'metadata (VM, databases)',
			'none' => 'none (media)'
		}
	);
	foreach my $key (sort(keys %zvol_createopts))
	{
		next if ($key eq 'refreservation');
		my $default_val = $zvol_createopts{$key} || 'default';
		if ($proplist{$key} eq 'text') {
			print ui_table_row($key.': ', ui_textbox($key, $default_val, 20)." (default: ".$default_val.")");
		} elsif ($zvol_descriptions{$key}) {
			my @options;
			push(@options, ['default', 'default']);
			foreach my $opt (split(", ", $proplist{$key})) {
				my $label = $zvol_descriptions{$key}{$opt} || $opt;
				push(@options, [$opt, $label]);
			}
			print ui_table_row($key.': ', ui_select($key, $default_val, \@options, 1, 0, 1));
		} else {
			my @options = split(", ", $proplist{$key});
			unshift(@options, 'default');
			if ($proplist{$key} eq 'boolean') { @options = ('default', 'on', 'off'); }
			print ui_table_row($key.': ', ui_select($key, $default_val, \@options, 1, 0, 1));
		}
	}
	print <<EOF;
<script type="text/javascript">
function validateFsForm(form) {
	var name = form.zfs.value;
	var nameRegex = /^[a-zA-Z0-9_\\-.:]+\$/;
	if (!name || !nameRegex.test(name)) {
		alert("Invalid Name. Please use alphanumeric characters, -, _, ., or :");
		return false;
	}
	var summary = "Create Filesystem Summary:\\n\\n";
	summary += "Name: " + form.parent.value + "/" + name + "\\n";
	summary += "Mountpoint: " + (form.mountpoint.value ? form.mountpoint.value : "Default") + "\\n";
	summary += "Recordsize: " + form.recordsize.value + "\\n";
	summary += "Compression: " + form.compression.value + "\\n";
	summary += "Atime: " + form.atime.value + "\\n";
	summary += "Sync: " + form.sync.value + "\\n";
	summary += "Exec: " + form.exec.value + "\\n";
	summary += "Canmount: " + form.canmount.value + "\\n";
	summary += "Xattr: " + form.xattr.value + "\\n";
	summary += "ACL Type: " + form.acltype.value + "\\n";
	summary += "ACL Inherit: " + form.aclinherit.value + "\\n";
	summary += "ACL Mode: " + form.aclmode.value + "\\n";
	summary += "ACL inherit flags: " + (form.add_inherit && form.add_inherit.checked ? "Yes" : "No") + "\\n";
	return confirm(summary);
}
function validateZvolForm(form) {
	var name = form.zfs.value;
	var nameRegex = /^[a-zA-Z0-9_\\-.:]+\$/;
	if (!name || !nameRegex.test(name)) {
		alert("Invalid Name. Please use alphanumeric characters, -, _, ., or :");
		return false;
	}
	var size = form.size.value;
	var regex = /^\\d+(\\.\\d+)?[KMGTP]?\$/i;
	if (!size || !regex.test(size)) {
		alert("Invalid size format. Please use format like 10G, 500M, etc.");
		return false;
	}
	var summary = "Create Volume Summary:\\n\\n";
	summary += "Name: " + form.parent.value + "/" + name + "\\n";
	summary += "Size: " + size + "\\n";
	summary += "Blocksize: " + form.volblocksize.value + "\\n";
	summary += "Compression: " + form.compression.value + "\\n";
	summary += "Sync: " + form.sync.value + "\\n";
	summary += "Logbias: " + form.logbias.value + "\\n";
	summary += "Primary Cache: " + form.primarycache.value + "\\n";
	summary += "Secondary Cache: " + form.secondarycache.value + "\\n";
	if (form.sparse.checked) {
		summary += "Sparse: Yes (Refreservation: " + form.refreservation.value + ")\\n";
	} else {
		summary += "Sparse: No (Thick provisioned)\\n";
	}
	return confirm(summary);
}
function updateRefres() {
	var sparse = document.getElementsByName("sparse")[0];
	var refres = document.getElementsByName("refreservation")[0];
	var size = document.getElementsByName("size")[0];
	var label = document.getElementById("refres_label");
	if (sparse.checked) {
		refres.disabled = false;
		var sVal = size.value ? size.value : "Size";
		label.innerHTML = " (maximum Size: " + sVal + "     default: none)";
	} else {
		refres.disabled = true;
		label.innerHTML = " (Volume is thick provisioned)";
	}
}
window.onload = function() { updateRefres(); };
</script>
EOF
	print ui_table_row('sparse:', ui_checkbox('sparse', '1', ' Create as sparse volume - reservation only', "onclick='updateRefres()'"));
	print ui_table_row('refreservation:', ui_textbox('refreservation', 'none', 20)."<span id='refres_label'></span>");
	print ui_table_end();
	print ui_submit('Create');
	print ui_form_end();
	print &ui_tabs_end_tab("mode", "zvol");

	#end tabs
	print &ui_tabs_end(1);
	$in{'zfs'} = $in{'parent'};
	
} elsif ($in{'import'}) {
	require_acl_permission('upool_properties', 'Permission denied');
	ui_print_header(undef, "Import Pool", "", undef, 1, 0);
	print ui_form_start("create.cgi", "get");
	print ui_hidden('import', '1');
	print ui_hidden('xnavigation', '1');
	print ui_hidden('do_search', '1');
	print ui_table_start("Import Zpool", 'width=100%');
	print ui_table_row(undef, "Import search directory (blank for default):".ui_filebox('dir', $in{'dir'}, 25, undef, undef, undef, 1));
	print ui_table_row(undef, ui_checkbox('destroyed', 1, 'Search for destroyed pools', $in{'destroyed'}));
	print ui_table_row(undef, ui_submit('Search', 'search'));
	print ui_table_end();
	print ui_form_end();
	if ($in{'do_search'} || $in{'search'}) {
		%imports = zpool_imports($in{'dir'}, $in{'destroyed'});
		if ($zpool_imports_error) {
			print "<b>Error:</b> ".h($zpool_imports_error)."<br />";
		}
		if (!%imports) {
			if ($in{'destroyed'}) {
				print "<b>No destroyed pools found.</b><br />";
			} else {
				print "<b>No exported pool to import!</b><br />";
			}
		} else {
			print ui_columns_start([ "Pool", "ID", "State" ]);
			foreach $key (sort(keys %imports))
			{
				my $pool = $imports{$key}{pool};
				my $id = $imports{$key}{'id'};
				my $state = $imports{$key}{'state'};
				my $pool_link = ui_post_action_link($pool, 'cmd.cgi',
					{ 'cmd' => 'import', 'import' => $pool, 'dir' => $in{'dir'}, 'destroyed' => $in{'destroyed'}, 'xnavigation' => 1 });
				my $id_link = ui_post_action_link($id, 'cmd.cgi',
					{ 'cmd' => 'import', 'import' => $id, 'dir' => $in{'dir'}, 'destroyed' => $in{'destroyed'}, 'xnavigation' => 1 });
				print ui_columns_row([$pool_link, $id_link, h($state)]);
			}
			print ui_columns_end();
		}
	}
	@footer = ('index.cgi?xnavigation=1', $text{'index_return'});
} elsif ($in{'clone'}) {
	require_acl_permission('uzfs_properties', 'Permission denied');
	ui_print_header(undef, "Clone Snapshot", "", undef, 1, 0);
	my %parent = find_parent($in{'clone'});
	print ui_form_start("cmd.cgi", "post", undef, "onsubmit='return validateClone(this)'");
	print ui_csrf_hidden();
	print ui_table_start('Clone Snapshot', 'width=100%', '6');
	print ui_table_row(undef, '<b>Snapshot:</b> '.h($in{'clone'}));
	print ui_table_row(undef, "<b>Name: </b>".$parent{'pool'}."/".ui_textbox('zfs'));
	print ui_table_row(undef, '<b>Mount point</b> (blank for default)'.ui_filebox('mountpoint', '', 25, undef, undef, 1));
	print ui_hidden('cmd', 'clone');
	print ui_hidden('clone', $in{'clone'});
	print ui_hidden('parent', $parent{'pool'});
	print ui_table_row(undef, "<br />");
	print ui_table_row(undef, '<b>File system options:</b> ');
	foreach $key (@fs_order)
	{
		my @options;
		push(@options, ['default', 'default']);
		my @raw_opts = ($proplist{$key} eq 'boolean') ? ('on', 'off') : split(", ", $proplist{$key});
		foreach my $opt (@raw_opts) {
			my $label = $fs_descriptions{$key}{$opt} || $opt;
			push(@options, [$opt, $label]);
		}
		my $default_val = $createopts{$key} || 'default';
		my %opt_seen = map { $_->[0] => 1 } @options;
		if ($default_val ne 'default' && !$opt_seen{$default_val}) {
			my $label = $fs_descriptions{$key}{$default_val} || $default_val;
			push(@options, [$default_val, $label]);
		}
		my $help = $acl_tooltips{$key} ? "<br><small><i>$acl_tooltips{$key}</i></small>" : "";
		my $selected = defined($in{$key}) ? $in{$key} : $default_val;
		print ui_table_row($key.': ', ui_select($key, $selected, \@options, 1, 0, 1).$help);
	}
	my $add_inherit_default = defined($in{'add_inherit'}) ? $in{'add_inherit'} : 1;
	print ui_table_row('ACL inherit flags:', ui_checkbox('add_inherit', 1, 'Add :fd to base NFSv4 ACL entries', $add_inherit_default));
	print ui_table_end();
	print ui_submit('Create');
	print ui_form_end();
	print <<EOF;
<script type="text/javascript">
function validateClone(form) {
	var name = form.zfs.value;
	var nameRegex = /^[a-zA-Z0-9_\\-.:]+\$/;
	if (!name || !nameRegex.test(name)) {
		alert("Invalid Name. Please use alphanumeric characters, -, _, ., or :");
		return false;
	}
	return true;
}
</script>
EOF
	$in{'snap'} = $in{'clone'};
} elsif ($in{'destroy_zfs'}) {
	require_acl_permission('uzfs_destroy', 'Permission denied');
	ui_print_header(undef, "Destroy Filesystem", "", undef, 1, 0);
	print ui_form_start("cmd.cgi", "post", undef, "onsubmit='return validateDestroy(this)'");
	print ui_csrf_hidden();
	print ui_table_start('Destroy Filesystem', 'width=100%', '6');
	print "<tr><td colspan='2'>";
	print "<b>Filesystem:</b> ".h($in{'destroy_zfs'})."<br /><br />";
	print "<b>Options</b><br />";
	print ui_checkbox("force", "-r", "Destroy all child dependencies (recursive).")."<br />";
	if ($^O eq 'freebsd') {
		print ui_checkbox("force_unmount", "-f", "Force unmount even if busy (FreeBSD).")."<br />";
	}
	print "<br /><b>$text{'cmd_affect'} </b><br />";
	ui_zfs_list('-r '.$in{'destroy_zfs'});
	ui_list_snapshots('-r '.$in{'destroy_zfs'});
	print "<br /><b>Confirmation</b><br />";
	print $text{'cmd_warning'}."<br />";
	print ui_checkbox('confirm', 'yes', $text{'cmd_understand'}, undef )."<br /><br />";
	print ui_submit($text{'continue'});
	print "</td></tr>";
	print ui_hidden('cmd', 'zfsdestroy');
	print ui_hidden('zfs', $in{'destroy_zfs'});
	print ui_table_end();
	print ui_form_end();
	print <<EOF;
<script type="text/javascript">
function validateDestroy(form) {
	if (!form.confirm.checked) {
		alert("Please confirm you understand the consequences.");
		return false;
	}
	return true;
}
</script>
EOF
	@footer = ("status.cgi?zfs=".u($in{'destroy_zfs'})."&xnavigation=1", h($in{'destroy_zfs'}));
} elsif ($in{'destroy_pool'}) {
	require_acl_permission('upool_destroy', 'Permission denied');
	ui_print_header(undef, "Destroy Pool", "", undef, 1, 0);
	print ui_form_start("cmd.cgi", "post", undef, "onsubmit='return validateDestroy(this)'");
	print ui_csrf_hidden();
	print ui_table_start('Destroy Pool', 'width=100%', '6');
	print "<tr>";
	print "<td valign='top' width='45%'>";
	print "<b>Pool:</b> ".h($in{'destroy_pool'})."<br /><br />";
	print "<b>Options</b><br />";
	print ui_checkbox("force", "-f", "Force unmount any active datasets.")."<br />";
	print "<br />";
	print "<b>Confirmation</b><br />";
	print $text{'cmd_warning'}."<br />";
	print ui_checkbox('confirm', 'yes', $text{'cmd_understand'}, undef ), "<br />";
	print "<br />";
	print ui_submit($text{'continue'});
	print "</td>";
	print "<td valign='top' width='55%'>";
	print "<b>$text{'cmd_affect'} </b><br />";
	ui_zfs_list('-r '.$in{'destroy_pool'});
	ui_list_snapshots('-r '.$in{'destroy_pool'});
	print "</td>";
	print "</tr>";
	print ui_hidden('cmd', 'pooldestroy');
	print ui_hidden('pool', $in{'destroy_pool'});
	print ui_table_end();
	print ui_form_end();
	print <<EOF;
<script type="text/javascript">
function validateDestroy(form) {
	if (!form.confirm.checked) {
		alert("Please confirm you understand the consequences.");
		return false;
	}
	return true;
}
</script>
EOF
	@footer = ("status.cgi?pool=".u($in{'destroy_pool'})."&xnavigation=1", h($in{'destroy_pool'}));
} elsif ($in{'rename'}) {
	require_acl_permission('uzfs_properties', 'Permission denied');
	ui_print_header(undef, "Rename", "", undef, 1, 0);
    print ui_form_start("cmd.cgi", "post", undef, "onsubmit='return validateRename(this)'");
	print ui_csrf_hidden();
	%parent = find_parent($in{'rename'});
	if (index($in{'rename'}, '@') != -1) {
		#is snapshot
		print ui_hidden('confirm', 'yes');
		$parent = $parent{'filesystem'};
		print ui_table_start('Rename snapshot', 'width=100%', '6');
       	print ui_table_row(undef, '<b>Snapshot:</b> '.h($in{'rename'}));
      	print ui_table_row(undef, "<b>New Name: </b>".$parent."@".ui_textbox('name', $parent{'snapshot'}, 35));
		print ui_table_row(undef, ui_checkbox("recurse", "-r ", "Recursively rename the snapshots of all descendent datasets."));
		@footer = ("status.cgi?snap=".u($in{'rename'})."&xnavigation=1", h($in{'rename'}));
	} elsif (index($in{'rename'}, '/') != -1) {
        #is filesystem
		$parent = $parent{'pool'};
		ui_zfs_list("-r ".$in{'rename'});
		print ui_table_start('Rename filesystem', 'width=100%', '6');
                print ui_table_row(undef, '<b>Filesystem:</b> '.h($in{'rename'}));
                print ui_table_row(undef, "<b>New Name: </b>".$parent."/".ui_textbox('name', undef, 35));
		print ui_table_row(undef, ui_checkbox("prnt", "-p ", "Create all the nonexistent parent datasets."));
	}
	print ui_table_row(undef, ui_checkbox("force", "-f ", "Force unmount any filesystems that need to be unmounted in the process.", 1));
        print ui_hidden('cmd', 'rename');
        print ui_hidden('zfs', $in{'rename'});
	print ui_hidden('parent', $parent);
        print ui_table_row(undef, "<br />");
        print ui_table_end();
        print ui_submit('Rename');
        print ui_form_end();
	print <<EOF;
<script type="text/javascript">
function validateRename(form) {
	var name = form.name.value;
	var nameRegex = /^[a-zA-Z0-9_\\-.:]+\$/;
	if (!name || !nameRegex.test(name)) {
		alert("Invalid Name. Please use alphanumeric characters, -, _, ., or :");
		return false;
	}
	return true;
}
</script>
EOF
	$in{'zfs'} = $in{'rename'};
} elsif (($in{'create'} =~ "snapshot") &&  ($in{'zfs'} eq undef)) {
	require_acl_permission('uzfs_properties', 'Permission denied');
	ui_print_header(undef, $text{'snapshot_new'}, "", undef, 1, 0);
	%zfs = list_zfs();
	print ui_columns_start([ "File System", "Used", "Avail", "Refer", "Mountpoint" ]);
	foreach $key (sort(keys %zfs)) 
	{
		my $link = "<a href='create.cgi?create=snapshot&zfs=".u($key)."&xnavigation=1'>".h($key)."</a>";
		print ui_columns_row([$link, h($zfs{$key}{used}), h($zfs{$key}{avail}), h($zfs{$key}{refer}), h($zfs{$key}{mount}) ]);
	}
	print ui_columns_end();
	@footer = ('index.cgi?mode=snapshot&xnavigation=1', $text{'snapshot_return'});
#handle creation of snapshot
} elsif ($in{'create'} =~ "snapshot") {
	require_acl_permission('uzfs_properties', 'Permission denied');
	ui_print_header(undef, $text{'snapshot_create'}, "", undef, 1, 0);
	%zfs = list_zfs($in{'zfs'});
	print ui_columns_start([ "File System", "Used", "Avail", "Refer", "Mountpoint" ]);
	foreach $key (sort(keys %zfs)) 
	{
		my $link = "<a href='status.cgi?zfs=".u($key)."&xnavigation=1'>".h($key)."</a>";
		print ui_columns_row([$link, h($zfs{$key}{used}), h($zfs{$key}{avail}), h($zfs{$key}{refer}), h($zfs{$key}{mount}) ]);
	}
	print ui_columns_end();
	#show list of snapshots based on filesystem
	print "Snapshots already on this filesystem: <br />";
	%snapshot = list_snapshots();
	print ui_columns_start([ "Snapshot", "Used", "Refer" ]);
	foreach $key (sort(keys %snapshot)) 
	{
		if (index($key, $in{'zfs'}."@") == 0 ) {
			my $link = "<a href='snapshot.cgi?snap=".u($key)."&xnavigation=1'>".h($key)."</a>";
			print ui_columns_row([$link, h($snapshot{$key}{used}), h($snapshot{$key}{refer}) ]);
		}
	}
	print ui_columns_end();
	print ui_create_snapshot($in{'zfs'});
}

if (@footer) { ui_print_footer(@footer); 
} elsif ($in{'zfs'} && !@footer) {
		print "<br />";
		ui_print_footer("status.cgi?zfs=".u($in{'zfs'})."&xnavigation=1", h($in{'zfs'}));
} elsif ($in{'pool'} && !@footer) {
		print "<br />";
		ui_print_footer("status.cgi?pool=".u($in{'pool'})."&xnavigation=1", h($in{'pool'}));
} elsif ($in{'snap'} && !@footer) {
		print "<br />";
		ui_print_footer("status.cgi?snap=".u($in{'snap'})."&xnavigation=1", h($in{'snap'}));
}
