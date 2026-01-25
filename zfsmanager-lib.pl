BEGIN { push(@INC, ".."); };
use WebminCore;
use POSIX qw(strftime WNOHANG);
use IO::Select;
init_config();
foreign_require("mount", "mount-lib.pl");
my %access = &get_module_acl();

sub properties_list
#return hash of properties that can be set manually and their data type
{
my %list = ('atime' => 'boolean', 'devices' => 'boolean', 'exec' => 'boolean', 'nbmand' => 'boolean', 'readonly' => 'boolean', 'setuid' => 'boolean', 'shareiscsi' => 'boolean', 'utf8only' => 'boolean', 'vscan' => 'boolean', 'zoned' => 'boolean', 'relatime' => 'boolean', 'overlay' => 'boolean',
			'aclinherit' => 'discard, noallow, restricted, passthrough, passthrough-x', 'aclmode' => 'discard, groupmaks, passthrough', 'casesensitivity' => 'sensitive, insensitive, mixed', 'checksum' => 'on, off, fletcher2, fletcher4, sha256', 'compression' => 'on, off, lzjb, lz4, gzip, gzip-1, gzip-2, gzip-3, gzip-4, gzip-5, gzip-6, gzip-7, gzip-8, gzip-9, zle, zstd, zstd-1, zstd-2, zstd-3, zstd-4, zstd-5, zstd-6, zstd-7, zstd-8, zstd-9, zstd-10, zstd-11, zstd-12, zstd-13, zstd-14, zstd-15, zstd-16, zstd-17, zstd-18, zstd-19', 'copies' => '1, 2, 3', 'dedup' => 'on, off, verify, sha256', 'logbias' => 'latency, throughput', 'normalization' => 'none, formC, formD, formKC, formKD', 'primarycache' => 'all, none, metadata', 'secondarycache' => 'all, none, metadata', 'snapdir' => 'hidden, visible', 'snapdev' => 'hidden, visible', 'sync' => 'standard, always, disabled', 'xattr' => 'on, off, sa', 'com.sun:auto-snapshot' => 'true, false', 'acltype' => 'noacl, posixacl', 'redundant_metadata' => 'all, most', 'recordsize' => '512, 1K, 2K, 4K, 8K, 16K, 32K, 64K, 128K, 256K, 512K, 1M', 'canmount' => 'on, off, noauto',
			'redundant_metadata' => 'all, most', 'recordsize' => '512, 1K, 2K, 4K, 8K, 16K, 32K, 64K, 128K, 256K, 512K, 1M, 2M, 4M', 'canmount' => 'on, off, noauto',
			'keylocation' => 'text', 'keystatus' => 'special','quota' => 'text', 'refquota' => 'text', 'reservation' => 'text', 'refreservation' => 'text', 'volsize' => 'text', 'filesystem_limit' => 'text', 'snapshot_limit' => 'text', 
			'mountpoint' => 'special', 'sharesmb' => 'special', 'sharenfs' => 'special', 'mounted' => 'special', 'context' => 'special', 'defcontext' => 'special', 'fscontext' => 'special', 'rootcontext' => 'special', 'volblocksize' => '512, 1K, 2K, 4K, 8K, 16K, 32K, 64K, 128K');
return %list;
}

sub pool_properties_list
{
my %list = ('autoexpand' => 'boolean', 'autoreplace' => 'boolean', 'delegation' => 'boolean', 'listsnapshots' => 'boolean', 
			'failmode' => 'wait, continue, panic', 'feature@async_destroy' => 'enabled, disabled', 'feature@empty_bpobj' => 'enabled, disabled', 'feature@lz4_compress' => 'enabled, disabled', 'feature@embedded_data' => 'enabled, disabled', 'feature@enabled_txg' => 'enabled, disabled', 'feature@bookmarks' => 'enabled, disabled', 'feature@hole_birth' => 'enabled, disabled', 'feature@spacemap_histogram' => 'enabled, disabled', 'feature@extensible_dataset' => 'enabled, disabled', 'feature@large_blocks' => 'enabled, disabled', 'feature@filesystem_limits' => 'enabled, disabled',
			'altroot' => 'special', 'bootfs' => 'special', 'cachefile' => 'special', 'comment' => 'special');
return %list;
}

sub create_opts #options and defaults when creating new pool or filesystem
{
my %list = (
    'atime'       => 'off',
    'compression' => 'lz4',
    'xattr'       => 'sa',
    'recordsize'  => '128K',
    'acltype'     => 'nfsv4',
    'aclinherit'  => 'passthrough',
    'aclmode'     => 'passthrough',
    'sync'        => 'disabled',
    'canmount'    => 'on',
    'exec'        => 'on',
);
return %list;
}

sub get_zfsmanager_config
{
my $lref = &read_file_lines($module_config_file);
my %rv;
my $lnum = 0;
foreach my $line (@$lref) {
    my ($n, $v) = split(/=/, $line, 2);
    if ($n) {
	  $rv{$n} = $v;
      }
    $lnum++;
    }
return %rv;
}

#determine if a property can be edited
sub can_edit
{
my ($zfs, $property) = @_;
%conf = get_zfsmanager_config();
%zfs_props = properties_list();
%pool_props = pool_properties_list();
my %type = zfs_get($zfs, 'type');
if ($type{$zfs}{type}{value} =~ 'snapshot') { return 0; } 
elsif ((($zfs_props{$property}) && ($config{'zfs_properties'} =~ /1/)) || (($pool_props{$property}) && ($config{'pool_properties'} =~ /1/))) { return 1; }
}

sub list_zpools
{
my ($pool) = @_;
my %hash=();
$list=`zpool list -H -o name,$config{'list_zpool'} $pool`;

open my $fh, "<", \$list;
while (my $line =<$fh>)
{
    chomp ($line);
	my @props = split(" ", $line);
        $ct = 1;
        foreach $prop (split(",", $config{'list_zpool'})) {
                $hash{$props[0]}{$prop} = $props[$ct];
                $ct++;
        }

}
return %hash;
}

sub list_zfs
{
#zfs list
my ($zfs) = @_;
my %hash=();
$list=`zfs list -H -o name,$config{'list_zfs'} $zfs`;

open my $fh, "<", \$list;
while (my $line =<$fh>)
{
	chomp ($line);
	my @props = split(" ", $line);
	$ct = 1;
	foreach $prop (split(",", $config{'list_zfs'})) { 
		$hash{$props[0]}{$prop} = $props[$ct];
		$ct++;
	}
}
return %hash;
}

sub list_snapshots
{
my ($snap) = @_;
$list=`zfs list -t snapshot -H -o name,$config{'list_snap'} -s creation $snap`;
$idx = 0;
open my $fh, "<", \$list;
while (my $line =<$fh>)
{
    chomp ($line);
    my @props = split("\x09", $line);
    $ct = 0;
    foreach $prop (split(",", "name,".$config{'list_snap'})) {
	    $hash{sprintf("%05d", $idx)}{$prop} = $props[$ct];
            $ct++;
    }
    $idx++;
}
return %hash;
}

sub get_alerts
{
my $alerts = `zpool status -x`;
my %status = ();
my $pool = ();
if ($alerts =~ /all pools are healthy/)
{
	return $alerts;
} else
{
	open my $fh, "<", \$alerts;
	while (my $line =<$fh>)
	{
		chomp ($line);
		$line =~ s/^\s*(.*?)\s*$/$1/;
		my($key, $value) = split(/:/, $line);
		$key =~ s/^\s*(.*?)\s*$/$1/;
		$value =~ s/^\s*(.*?)\s*$/$1/;
		if (($key =~ 'pool') && ($value))
		{
			$pool = $value;
			$status = ( $value );
		} elsif ((($key =~ 'state') || ($key =~ 'errors')) && ($value))
		{
			$status{$pool}{$key} = $value;
		}
	}
	my $out = "<b>";
	foreach $key (sort(keys %status))
	{
		%zstat = zpool_status($key);
		$out .= "pool \'".$key."\' is ".$zstat{0}{state}." with ".$zstat{0}{errors}."<br />";
		if ($zstat{0}{status}) { $out .= "status: ".$zstat{0}{status}."<br />"; }
		$out .= "<br />";
	}
	$out .= "</b>";
	return $out;
}
}

#zpool_status($pool)
sub zpool_status
{
my ($pool)=@_;
my %status = ();
my $cmd=`zpool status $pool`;
my @lines = split(/\n/, $cmd);

$status{0}{pool} = $pool;
my $in_config = 0;
my $devs = 1;
my $parent = "pool";

foreach my $line (@lines) {
    chomp ($line);
    if ($line =~ /^\s*pool:\s+(.*)/) { $status{0}{pool} = $1; }
    elsif ($line =~ /^\s*state:\s+(.*)/) { $status{0}{state} = $1; }
    elsif ($line =~ /^\s*scan:\s+(.*)/) { $status{0}{scan} = $1; }
    elsif ($line =~ /^\s*status:\s+(.*)/) { $status{0}{status} .= $1 . " "; }
    elsif ($line =~ /^\s*action:\s+(.*)/) { $status{0}{action} .= $1 . " "; }
    elsif ($line =~ /^\s*see:\s+(.*)/) { $status{0}{see} = $1; }
    elsif ($line =~ /^\s*errors:\s+(.*)/) { $status{0}{errors} = $1; }
    elsif ($line =~ /^\s*config:/) { $in_config = 1; next; }
    
    if ($in_config) {
        next if ($line =~ /^\s*NAME\s+/);
        next if ($line =~ /^\s*$/);
        last if ($line =~ /^\s*errors:/);
        
        my $trimmed = $line;
        $trimmed =~ s/^\s+//;
        my ($name, $state, $read, $write, $cksum) = split(/\s+/, $trimmed);
        
        next unless $name;
        
        if ($name eq $status{0}{pool}) {
            $status{0}{name} = $name;
            $status{0}{read} = $read;
            $status{0}{write} = $write;
            $status{0}{cksum} = $cksum;
        } elsif ($name =~ /^(mirror|raidz|draid|spare|log|cache|special)/) {
             $status{$devs} = {name => $name, state => $state, read => $read, write => $write, cksum => $cksum, parent => "pool"};
             $parent = $devs;
             $devs++;
        } else {
             $status{$devs} = {name => $name, state => $state, read => $read, write => $write, cksum => $cksum, parent => $parent};
             $devs++;
        }
    }
}
return %status;
}

sub get_pool_details
{
my %info;
my $current_pool = undef;
my $in_config = 0;

# 1. Parse zpool status for Health and RAID level
my $status_output = `zpool status`;

foreach my $line (split(/\n/, $status_output)) {
    if ($line =~ /^\s*pool:\s*(\S+)/) {
        $current_pool = $1;
        $info{$current_pool} = { raid => 'BASIC', health => 'UNKNOWN' };
        $in_config = 0;
        next;
    }

    # Skip lines if we're not inside a pool's status block
    next unless $current_pool;

    if ($current_pool && $line =~ /^\s*state:\s*(\S+)/) {
        $info{$current_pool}->{health} = $1;
    }

    if ($line =~ /^\s*config:/) {
        $in_config = 1;
        next;
    }

    # Stop parsing when the config section ends
    # A non-indented, non-empty line (like "errors:") signifies the end of the config block.
    if ($in_config && $line =~ /^\S/) {
        $in_config = 0;
        next;
    }

    if ($in_config && $current_pool) {
        my $trimmed = $line;
        $trimmed =~ s/^\s+//;
        my ($name) = split(/\s+/, $trimmed);
        
        # Find the first vdev that defines the RAID level (mirror, raidz, etc.)
        if ($info{$current_pool}->{raid} eq 'BASIC' && $name =~ /^(mirror|raidz\d*|draid)/) {
            my ($raid_type) = ($name =~ /^(mirror|raidz\d*|draid\d*)/);
            if ($raid_type) {
                $info{$current_pool}->{raid} = uc($raid_type);
            }
        }
    }
}

return %info;
}

sub from_iec {
    my ($size_str) = @_;
    return 0 unless defined $size_str && $size_str =~ /^([\d\.]+)([KMGTP]?)/i;
    my $num = $1;
    my $unit = uc($2 || '');
    my %multipliers = (
        '' => 1,
        'K' => 1024,
        'M' => 1024**2,
        'G' => 1024**3,
        'T' => 1024**4,
        'P' => 1024**5,
    );
    return $num * ($multipliers{$unit} || 1);
}

sub to_iec {
    my ($bytes) = @_;
    return '0B' if !$bytes || $bytes == 0;
    my @units = ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB');
    my $i = 0;
    while ($bytes >= 1024 && $i < $#units) {
        $bytes /= 1024;
        $i++;
    }
    # Use sprintf to format to 2 decimal places for non-byte values
    return $i == 0 ? int($bytes).'B' : sprintf("%.2f%s", $bytes, $units[$i]);
}

#zfs_get($pool, $property)
sub zfs_get
{
my ($zfs, $property) = @_;
if (~$property) {my $property="all";}
my %hash=();
my $get=`zfs get -H $property $zfs`;
open my $fh, "<", \$get;
while (my $line =<$fh>)
{
    chomp ($line);
    my($name, $property, $value, $source) = split(/\t/, $line);
	$hash{$name}{$property} = { value => $value, source => $source };
}
return %hash;
}

#zpool_get($pool, $property)
sub zpool_get
{
my ($pool, $property) = @_;
if (~$property) {my $property="all";}
my %hash=();
my $get=`zpool get -H $property $pool`;

open my $fh, "<", \$get;
while (my $line =<$fh>)
{
    chomp ($line);
	my($name, $property, $value, $source) = split(/\t/, $line);
	$hash{$name}{$property} = { value => $value, source => $source };
}
return %hash;
}

sub zpool_imports
{
my ($dir, $destroyed) = @_;
if ($dir) { $dir = '-d '.$dir; }
my %status = ();
my $cmd = `zpool import $dir $destoryed`;
$count = 0;
@pools = split(/  pool: /, $cmd);
shift (@pools);
foreach $cmdout (@pools) {
	($status{$count}{pool}, $cmdout) = split(/ id: /, $cmdout);
	chomp $status{$count}{pool};
	$status{$count}{pool} =~ s/^\s+|\s+$//g;
	($status{$count}{id}, $cmdout) = split(/ state: /, $cmdout);
	chomp $status{$count}{id};
	$status{$count}{id} =~ s/^\s+|\s+$//g;
	if (index($cmdout, "status: ") != -1) { 
		($status{$count}{state}, $cmdout) = split("status: ", $cmdout); 
		($status{$count}{status}, $cmdout) = split("action: ", $cmdout); 
		if (index($cmdout, "  see: ") != -1) { 
			($status{$count}{action}, $cmdout) = split("  see: ", $cmdout); 
			($status{$count}{see}, $cmdout) = split("config:\n", $cmdout); 
		} else { ($status{$count}{action}, $cmdout) = split("config:\n", $cmdout); }
	} else {
		($status{$count}{state}, $cmdout) = split("action: ", $cmdout); 
		($status{$count}{action}, $cmdout) = split("config:\n", $cmdout);
	}
	$status{$count}{config} = $cmdout;
$count++;
}
return %status;
}

sub diff
{
my ($snap, $parent) = @_;
my @array = split("\n", `zfs diff -FH $snap`);
return @array;
}


sub list_disk_ids
{
	my ($filter_boot, $filter_used) = @_;
	# Default filter_boot to 1 (hide boot) if not specified, to match legacy behavior
	$filter_boot = 1 if !defined $filter_boot;

	my %hash;
	use Cwd 'abs_path';

	# 1. Get ZFS devices cache
	my ($pools, $zfs_devices) = build_zfs_devices_cache();

	# 2. Get a list of all block devices (disks and partitions) on the system.
	my @all_devices;
	my %parent_disks;
	my %class_info;
	my %geom_partitions;

	if ($^O eq 'linux') {
		my @lines = `lsblk -P -o NAME,TYPE,FSTYPE,LABEL,PARTLABEL,PARTTYPE,UUID,PARTUUID,SIZE,PKNAME 2>/dev/null`;
		foreach my $line (@lines) {
			my %row = ();
			while ($line =~ /(\w+)="([^"]*)"/g) {
				$row{$1} = $2;
			}
			my $name = $row{'NAME'};
			next unless $name;
			my $dev_path = "/dev/$name";
			push @all_devices, $dev_path;

			if ($row{'TYPE'} eq 'disk') {
				$parent_disks{$dev_path} = 1;
			}

			my $base = $row{'PKNAME'} || $name;
			my $part_num = ($name =~ /(\d+)$/) ? $1 : undef;

			my ($fmt, $usage, $role) = classify_partition_row(
				'base_device' => $base,
				'part_name'   => $name,
				'part_num'    => $part_num,
				'part_label'  => $row{'PARTLABEL'} || $row{'LABEL'},
				'entry_part_type' => $row{'FSTYPE'} || $row{'PARTTYPE'},
				'entry_rawtype'   => $row{'PARTTYPE'},
				'size_human'      => $row{'SIZE'},
				'zfs_devices'     => $zfs_devices
			);
			$class_info{$dev_path} = {
				format => $fmt,
				usage => $usage,
				role => $role
			};
		}
	}
	elsif ($^O eq 'freebsd') {
		# For FreeBSD, use sysctl to get disks, and gpart to get partitions.
		my @disks = split(' ', `sysctl -n kern.disks 2>/dev/null`);
		foreach my $disk (@disks) {
			push @all_devices, "/dev/$disk";
			$parent_disks{"/dev/$disk"} = 1;

			my $ds = get_disk_structure($disk);
			if ($ds && $ds->{'entries'}) {
				foreach my $entry (@{$ds->{'entries'}}) {
					next unless $entry->{'type'} eq 'partition';

					my $idx = $entry->{'index'};
					my $p_name;
					if ($ds->{'partitions'} && $ds->{'partitions'}->{$idx}) {
						$p_name = $ds->{'partitions'}->{$idx}->{'name'};
					}
					unless ($p_name) {
						my $sep = ($ds->{'scheme'} =~ /GPT/i) ? 'p' : 's';
						$p_name = $disk . $sep . $idx;
					}
					my $dev_path = "/dev/$p_name";
					push @all_devices, $dev_path;

					my ($fmt, $usage, $role) = classify_partition_row(
						'base_device' => $disk,
						'scheme' => $ds->{'scheme'},
						'part_num' => $idx,
						'part_name' => $p_name,
						'part_label' => $entry->{'label'},
						'entry_part_type' => $entry->{'part_type'},
						'entry_rawtype' => $entry->{'rawtype'},
						'size_blocks' => $entry->{'size'},
						'size_human' => $entry->{'size_human'},
						'zfs_devices' => $zfs_devices
					);
					$class_info{$dev_path} = {
						format => $fmt,
						usage => $usage,
						role => $role
					};
				}
			}
		}
		# Check for GEOM mirror/stripe components
		foreach my $geom_cmd ("gmirror", "gstripe") {
			my $out = `$geom_cmd status 2>/dev/null`;
			while ($out =~ /\s+([a-z]+\d+p?\d*)\s+\(/g) {
				$geom_partitions{"/dev/$1"} = 1;
			}
		}
	}

	# 3. Identify parent disks that contain partitions.
	my %parents_with_partitions;
	foreach my $dev (@all_devices) {
		next if $parent_disks{$dev};
		my $parent;
		if ($dev =~ m{^(/dev/nvme\d+n\d+)p\d+$}) {
			$parent = $1;  # NVMe partition
		} elsif ($dev =~ m{^(/dev/[a-z]+\d+)p\d+$}) {
			$parent = $1;  # FreeBSD style (ada0p1 -> ada0)
		} elsif ($dev =~ m{^(/dev/[a-z]+)\d+$}) {
			$parent = $1;  # Linux style (sda1 -> sda)
		}
		if ($parent && $parent_disks{$parent}) {
			$parents_with_partitions{$parent} = 1;
		}
	}

	# 3.5. Build a map of canonical paths to /dev/disk/by-id names
	my %by_id_map;
	if (opendir(my $dh, "/dev/disk/by-id")) {
		while (my $entry = readdir($dh)) {
			next if $entry =~ /^\./;
			next unless $entry =~ /^(nvme|ata|scsi|wwn)-/;
			my $path = "/dev/disk/by-id/$entry";
			my $real = abs_path($path);
			if (!exists $by_id_map{$real}) {
				$by_id_map{$real} = $path;
			} else {
				# Prefer nvme > ata > scsi > wwn
				my $curr = $by_id_map{$real};
				my $score_curr = ($curr =~ /nvme/) ? 4 : ($curr =~ /ata/) ? 3 : ($curr =~ /scsi/) ? 2 : 1;
				my $score_new = ($entry =~ /nvme/) ? 4 : ($entry =~ /ata/) ? 3 : ($entry =~ /scsi/) ? 2 : 1;
				if ($score_new > $score_curr) { $by_id_map{$real} = $path; }
			}
		}
		closedir($dh);
	}

	# 4. Build the final list for the UI.
	foreach my $device (sort @all_devices) {
		# Skip parent disks that have partitions - only show partitions
		next if $parents_with_partitions{$device};
		my $canonical_device = -e $device ? abs_path($device) : $device;
		my $display_device = $by_id_map{$canonical_device} || $device;
		my ($model, $serial, undef, $size) = get_disk_details($device);
		my $desc = "";
		if ($model ne "-" || $serial ne "-") {
			$desc = " ($size) ($model, $serial)";
		}

		my $html_label = "$display_device$desc";

		if (my $info = $class_info{$device}) {
			if ($filter_boot && $info->{'role'} =~ /Boot/i) {
				next;
			}

			my $is_used = 0;
			if ($info->{'usage'} =~ /In ZFS pool/) { $is_used = 1; }
			elsif ($info->{'format'} eq 'Swap') { $is_used = 1; }
			elsif ($geom_partitions{$device}) { $is_used = 1; }

			if ($filter_used && $is_used) { next; }

			if ($info->{'usage'} =~ /In ZFS pool/) {
				$html_label = "<span style='color:red;'>$display_device$desc [$info->{'usage'}]</span>";
			} elsif ($info->{'format'} eq 'Swap') {
				$html_label = "<span style='color:red;'>$display_device$desc [SWAP]</span>";
			} elsif ($geom_partitions{$device}) {
				$html_label = "<span style='color:red;'>$display_device$desc [GEOM]</span>";
			} else {
				if ($info->{'usage'}) {
					if ($info->{'usage'} =~ /Unused|No usage/i) {
						$html_label .= " [Available]";
					} else {
						$html_label .= " [" . $info->{'usage'} . "]";
					}
				}
			}
		} else {
			# Fallback (Linux or unclassified)
			my $zfs_info = _find_in_zfs($zfs_devices, $device, $canonical_device);
			if ($filter_used && ($zfs_info || $geom_partitions{$device})) { next; }

			if ($zfs_info) {
				$html_label = "<span style='color:red;'>$display_device$desc [" . $zfs_info->{'pool'} . "]</span>";
			} elsif ($geom_partitions{$device}) {
				$html_label = "<span style='color:red;'>$display_device$desc [GEOM]</span>";
			}
		}

		$hash{'byid'}{$html_label} = $display_device;
	}
	return \%hash;
}

sub cmd_create_zfs
#deprecated
{
my ($zfs, $options)  = @_;
my $opts = ();
my %createopts = create_opts();
$createopts{'volblocksize'} = '16k';
if (${$options}{'sparse'}) { $opts .= "-s "; }
delete ${$options}{'sparse'};
my $is_zvol = 0;
if (${$options}{'zvol'}) { 
	$is_zvol = 1;
	$zfs = "-V ".${$options}{'zvol'}." ".$zfs; 
	delete ${$options}{'zvol'};
}
my %zvol_invalid = map { $_ => 1 } qw(aclinherit aclmode acltype atime canmount exec filesystem_limit mountpoint quota recordsize setuid snapshot_limit version xattr zoned casesensitivity normalization utf8only overlay);
foreach $key (sort(keys %${options}))
{
	next if ($is_zvol && $zvol_invalid{$key});
	$opts = (($createopts{$key}) && (${$options}{$key} =~ 'default')) ? $opts : $opts.' -o '.$key.'='.${$options}{$key};
}
my $cmd="zfs create $opts $zfs";
return $cmd;
}

sub cmd_create_zpool
#deprecated
{
my ($pool, $dev, $options, $poolopts, $force) = @_;
my $opts = ();
foreach $key (sort(keys %{$poolopts}))
{
	$opts = (${$poolopts}{$key} =~ 'default') ? $opts : $opts.' -o '.$key.'='.${$poolopts}{$key};
}
foreach $key (sort(keys %{$options}))
{
	$opts = (${$options}{$key} =~ 'default') ? $opts : $opts.' -O '.$key.'='.${$options}{$key};
}
my $cmd="zpool create $force $opts $pool $dev";
return $cmd;
}

sub get_pool_only_property_keys {
    my %keys = (
        'size' => 1, 'capacity' => 1, 'altroot' => 1, 'health' => 1,
        'guid' => 1, 'version' => 1, 'bootfs' => 1, 'delegation' => 1,
        'autoreplace' => 1, 'cachefile' => 1, 'failmode' => 1,
        'listsnapshots' => 1, 'autoexpand' => 1, 'dedupditto' => 1,
        'dedupratio' => 1, 'free' => 1, 'allocated' => 1,
        'ashift' => 1, 'comment' => 1, 'expandsize' => 1, 'freeing' => 1,
        'fragmentation' => 1, 'leaked' => 1,
    );
    return %keys;
}

sub ui_zpool_properties
{
my ($pool) = @_;
require './property-list-en.pl';
my %hash = zpool_get($pool, "all");
my %props =  property_desc();
my %settable_pool_props = pool_properties_list();
my %read_only_pool_props = get_pool_only_property_keys();

my @rows = ();
foreach $key (sort(keys %{$hash{$pool}}))
{
    # Filter: Show only if it's a known pool property or a feature flag
    next if (!exists($read_only_pool_props{$key}) && !exists($settable_pool_props{$key}) && $key !~ /^feature@/);

	my $label = $key;
	# Link to editor if it's a settable property
	if (exists($settable_pool_props{$key}) || ($props{$key}) || ($text{'prop_'.$key})) {
		$label = '<a href="property.cgi?pool='.$pool.'&property='.$key.'&xnavigation=1">'.$key.'</a>';
	}
	push(@rows, [ $label, $hash{$pool}{$key}{value} ]);
}
ui_properties_columns("Pool Properties", \@rows);
}

sub find_parent
{
my ($filesystem) = @_;
my %parent = ();
($parent{'pool'}) = split(/[@\/]/g, $filesystem);
$null = reverse $filesystem =~ /[@\/]/g;
$parent{'filesystem'} = substr $filesystem, 0, $-[0];
if (index($filesystem, '@') != -1) { (undef, $parent{'snapshot'}) = split(/@/, $filesystem); }
return %parent;
}

sub ui_zpool_list
{
my ($pool, $action)=@_;
my %zpool_info = list_zpools($pool);
my %zfs_info   = list_zfs($pool);
my %pool_details = get_pool_details();

if ($action eq undef) { $action = "status.cgi?pool="; }

# Define the new column headers
my @headers = ("Pool Name", "Size", "Allocated", "Free");
# Add other configured columns, but exclude the ones we are overriding
my @other_props = grep { $_ ne 'size' && $_ ne 'alloc' && $_ ne 'free' && $_ ne 'health' } split(/,/, $config{list_zpool});
push(@headers, @other_props);
print ui_columns_start(\@headers);

foreach my $key (sort(keys %zfs_info))
{
    next if !$zpool_info{$key}; # Skip if zpool data doesn't exist for this zfs entry

    # New logic for size, alloc, and free
    # Use native Perl functions to avoid external dependencies on bc/numfmt
    my $zfs_used_bytes = from_iec($zfs_info{$key}{'used'});
    my $zfs_avail_bytes = from_iec($zfs_info{$key}{'avail'});
    my $size_val = to_iec($zfs_used_bytes + $zfs_avail_bytes)."<br><small>($zpool_info{$key}{'size'})</small>";
    my $alloc_val = "$zfs_info{$key}{'used'}<br><small>($zpool_info{$key}{'alloc'})</small>";
    my $free_val  = "$zfs_info{$key}{'avail'}<br><small>($zpool_info{$key}{'free'})</small>";
    
    my $details = $pool_details{$key};
    my $health = $details->{health} || 'UNKNOWN';
    my $raid = $details->{raid} || 'BASIC';
    
    my $pool_col = "<a href='$action$key'>$key</a><br><small>$raid-$health</small>";

    my @vals = ($pool_col, $size_val, $alloc_val, $free_val);
    # Add the other properties from zpool list
    foreach my $prop (@other_props) {
        push(@vals, $zpool_info{$key}{$prop});
    }

    print ui_columns_row(\@vals);
}
print ui_columns_end();
}

sub ui_zfs_list
{
my ($zfs, $action, $exclude)=@_;
my %zfs = list_zfs($zfs);
if (scalar(keys %zfs) == 0 || (scalar(keys %zfs) == 1 && $exclude && exists($zfs{$exclude}))) {
	# Do not print the table if there is nothing to show (except the excluded parent)
	return;
}
if ($action eq undef) { $action = "status.cgi?zfs="; }
@props = split(/,/, $config{list_zfs});
print ui_columns_start([ "file system", @props ]);
foreach $key (sort(keys %zfs)) 
{
	next if ($exclude && $key eq $exclude);
	@vals = ();
	if ($zfs{$key}{'mountpoint'}) { $zfs{$key}{'mountpoint'} = "<a href='../filemin/index.cgi?path=".urlize($zfs{$key}{mountpoint})."&xnavigation=1'>$zfs{$key}{mountpoint}</a>"; }
	foreach $prop (@props) { push (@vals, $zfs{$key}{$prop}); }
    	print ui_columns_row(["<a href='$action$key'>$key</a>", @vals ]);
}
print ui_columns_end();
}

sub ui_zpool_status
#deprecated
{
my ($pool, $action) = @_;
if ($action eq undef) { $action = "status.cgi?pool="; }
my %zpool = list_zpools($pool);
print ui_columns_start([ "Pool Name", "Size", "Alloc", "Free", "Frag", "Cap", "Dedup", "Health"]);
}

sub ui_zfs_properties
{
my ($zfs)=@_;
require './property-list-en.pl';
my %hash = zfs_get($zfs, "all");

# Get the list of pool-only properties to exclude them
my %settable_pool_props = pool_properties_list();
my %read_only_pool_props = get_pool_only_property_keys();

if (!$hash{$zfs}{'com.sun:auto-snapshot'}) { $hash{$zfs}{'com.sun:auto-snapshot'}{'value'} = '-'; }
my %props = property_desc();
my %properties = properties_list(); # This is for settable filesystem properties
my @rows = ();
foreach $key (sort(keys %{$hash{$zfs}}))
{
    # Exclude pool-only properties and features
    next if (exists($read_only_pool_props{$key}) || exists($settable_pool_props{$key}) || $key =~ /^feature@/);

	my $label = $key;
	my $value = $hash{$zfs}{$key}{value};
	if (($properties{$key}) || ($props{$key}) || ($text{'prop_'.$key}))
	{
		$label = '<a href="property.cgi?zfs='.$zfs.'&property='.$key.'&xnavigation=1">'.$key.'</a>';
		if ($key =~ 'origin') {
			$value = "<a href='status.cgi?snap=$value&xnavigation=1'>$value</a>";
		} elsif ($key =~ 'clones') {
			$row = "";
			@clones = split(',', $value);
			foreach $clone (@clones) { $row .= "<a href='status.cgi?zfs=$clone&xnavigation=1'>$clone</a> "; }
			$value = $row;
		}
	}
	push(@rows, [ $label, $value ]);
}
ui_properties_columns("Filesystem Properties", \@rows);
}

sub ui_properties_columns
{
	my ($title, $rows, $cols) = @_;
	my $total = scalar(@$rows);
	return if $total == 0;

	# Prepare cells for ui_grid_table
	my @cells;
	foreach my $row (@$rows) {
		my ($k, $v) = @{$row};
		my $k_wrap = $k;
		$k_wrap =~ s/_/_<wbr>/g;
		$k_wrap =~ s/\@/\@<wbr>/g;

		my $cell_content = "<div style='border:1px solid #eee; border-radius:3px; padding:4px 6px; background:#fafafa; width:100%; box-sizing:border-box; height: 100%;'>".
						   "<div style='font-weight:600; word-break:break-all;'>".$k_wrap."</div>".
						   "<div style='word-break:break-all;'>".$v."</div>".
						   "</div>";
		push(@cells, $cell_content);
	}

	# Set number of columns
	if (!$cols) {
		$cols = 4;
	}

	print ui_grid_table(\@cells, $cols, 100, "cellpadding=5", undef, $title);
}

sub ui_list_snapshots
{
my ($zfs, $admin) = @_;
%snapshot = list_snapshots($zfs);
@props = split(/,/, $config{list_snap});
if ($admin =~ /1/) { 
	print ui_form_start('cmd.cgi', 'post');
	print ui_hidden('cmd', 'multisnap');
	}
print ui_columns_start([ "snapshot", @props ]);
my $num = 0;
foreach $key (sort(keys %snapshot))
{
	@vals = ();
	foreach $prop (@props) { push (@vals, $snapshot{$key}{$prop}); }
	if ($admin =~ /1/) {
		print ui_columns_row([ui_checkbox("select", $snapshot{$key}{name}.";", "<a href='status.cgi?snap=$snapshot{$key}{'name'}&xnavigation=1'>$snapshot{$key}{'name'}</a>"), @vals ]);
		$num ++;
	} else {
		print ui_columns_row([ "<a href='status.cgi?snap=$snapshot{$key}{name}&xnavigation=1'>$snapshot{$key}{name}</a>", @vals ]);
	}
}
print ui_columns_end();
if ($admin =~ /1/) { print select_all_link('select', '', "Select All"), " | ", select_invert_link('select', '', "Invert Selection") }
if (($admin =~ /1/) && ($config{'snap_destroy'} =~ /1/)) { print " | ".ui_submit("Destroy selected snapshots"); }
if ($admin =~ /1/) { print ui_form_end(); }

}

sub ui_create_snapshot
{
my ($zfs) = @_;
$rv = ui_form_start('cmd.cgi', 'post')."\n";
$rv .= "Create new snapshot based on filesystem: ".$zfs."<br />\n";
my $date = strftime "zfs_manager_%Y-%m-%d-%H%M", localtime;
$rv .= $zfs."@ ".ui_textbox('snap', $date, 28)."\n";
$rv .= ui_hidden('zfs', $zfs)."\n";
$rv .= ui_hidden('cmd', "snapshot")."\n";
$rv .= ui_submit("Create");
$rv .= ui_form_end();
return $rv;
}

sub ui_cmd
{
my ($message, $cmd, $timeout) = @_;
print "$text{'cmd_'.$in{'cmd'}} $message $text{'cmd_with'}<br />\n";
print "<i># ".$cmd."</i><br /><br />\n";
if (!$in{'confirm'}) {
	print ui_form_start('cmd.cgi', 'post');
	foreach $key (keys %in) {
		print ui_hidden($key, $in{$key});
	}
	print ui_hidden('confirm', 'yes');
	print "<h3>Would you like to continue?</h3>\n";
	print ui_submit("yes")."<br />";
	print ui_form_end();
} else {
	my @result;
	my $exit = 0;
	my $timed_out = 0;
	if ($timeout) {
		($exit, $timed_out, @result) = run_cmd_with_timeout($cmd, $timeout);
	} else {
		@result = (`$cmd 2>&1`);
	}
	if ($timed_out) {
		print "<b>error: </b>Command timed out after ${timeout}s.<br />\n";
		foreach $key (@result) { print $key."<br />\n"; }
	} elsif ($timeout ? ($exit == 0) : !$result[0]) {
		print "Success! <br />\n";
	} else	{
		print "<b>error: </b>".($result[0] || "Command failed.")."<br />\n";
		foreach $key (@result[1..@result]) { print $key."<br />\n"; }
	}
}
print "<br />";
}

sub run_cmd_with_timeout
{
my ($cmd, $timeout) = @_;
$timeout ||= 30;
my $pid = open(my $fh, "-|");
if (!defined $pid) {
	return (1, 0, "Failed to fork command.");
}
if ($pid == 0) {
	setpgrp(0, 0);
	exec($cmd." 2>&1");
	exit 127;
}
my $output = "";
my $timed_out = 0;
my $start = time;
my $sel = IO::Select->new($fh);
while (1) {
	my $elapsed = time - $start;
	last if $elapsed >= $timeout;
	my $remaining = $timeout - $elapsed;
	my @ready = $sel->can_read($remaining);
	last unless @ready;
	my $buf = "";
	my $read = sysread($fh, $buf, 4096);
	if (!defined $read) { next; }
	if ($read == 0) { last; }
	$output .= $buf;
}
if ((time - $start) >= $timeout) {
	$timed_out = 1;
	kill 'TERM', -$pid;
	sleep 1;
	kill 'KILL', -$pid;
}
my $tries = 0;
while (waitpid($pid, WNOHANG) == 0 && $tries < 5) {
	sleep 1;
	$tries++;
}
my $exit = $? >> 8;
my @lines = split(/\n/, $output);
return ($exit, $timed_out, @lines);
}

sub ui_cmd_old
{
my ($message, $cmd) = @_;
$rv = "Attempting to $message with command... <br />\n";
$rv .= "<i># ".$cmd."</i><br /><br />\n";
if (!$in{'confirm'}) {
        $rv .= ui_form_start('cmd.cgi', 'post');
        foreach $key (keys %in) {
                        $rv .= ui_hidden($key, $in{$key});
        }
        $rv .= "<h3>Would you like to continue?</h3>\n";
        $rv .= ui_submit("yes", "confirm", 0)."<br />";
        $rv .= ui_form_end();
} else {
        @result = (`$cmd 2>&1`);
        if (!$result[0])
        {
                $rv .= "Success! <br />\n";
        } else  {
        $rv .= "<b>error: </b>".$result[0]."<br />\n";
        foreach $key (@result[1..@result]) {
                $rv .= $key."<br />\n";
        }
        }
}

return $rv;
}



sub ui_popup_link
#deprecated
{
my ($name, $url)=@_;
return "<a onClick=\"\window.open('$url', 'cmd', 'toolbar=no,menubar=no,scrollbars=yes,width=600,height=400,resizable=yes'); return false\"\ href='$url'>$name</a>";
}

sub test_function
{

}

my %glabel_cache;
my $glabel_cached = 0;

sub resolve_glabel
{
    my ($dev) = @_;
    return $dev unless ($^O eq 'freebsd');
    
    if (!$glabel_cached) {
        my $out = `glabel status 2>/dev/null`;
        foreach my $line (split(/\n/, $out)) {
            if ($line =~ /^\s*(\S+)\s+\S+\s+(\S+)/) {
                $glabel_cache{$1} = $2;
            }
        }
        $glabel_cached = 1;
    }
    return $glabel_cache{$dev} || $dev;
}

sub get_smart_status
{
my ($dev) = @_;
return "" if ($dev =~ /mirror|raidz|draid|spare|log|cache/);

my $dev_path = $dev;

# Resolve label if FreeBSD
if ($^O eq 'freebsd') { $dev_path = resolve_glabel($dev); }

if ($dev !~ /^\//) {
    $dev_path = "/dev/$dev";
}

# Resolve partition to disk
if ($dev_path =~ m{^(/dev/nvme\d+n\d+)p\d+$}) {
    $dev_path = $1;
} elsif ($dev_path =~ m{^(/dev/[a-z]+\d+)p\d+$}) {
    $dev_path = $1;
} elsif ($dev_path =~ m{^(/dev/[a-z]+)\d+$}) {
    $dev_path = $1;
}

return "" unless (-e $dev_path);

my $smartctl = `which smartctl 2>/dev/null`;
chomp $smartctl;
return "" unless $smartctl;

my $out = `$smartctl -H $dev_path 2>/dev/null`;
if ($out =~ /PASSED/) {
    return "<font color='green'>PASSED</font>";
} elsif ($out =~ /FAILED/) {
    return "<font color='red'>FAILED</font>";
}
return "";
}

sub get_disk_details
{
my ($dev) = @_;
return ("-", "-", "-", "-") if ($dev =~ /mirror|raidz|draid|spare|log|cache|special/);

my $dev_path = $dev;

# Resolve label if FreeBSD
if ($^O eq 'freebsd') { $dev_path = resolve_glabel($dev); }

if ($dev_path !~ /^\//) { $dev_path = "/dev/$dev_path"; }

# Determine parent disk for Model/Serial/Temp
my $parent_disk = $dev_path;
if ($parent_disk =~ m{^(/dev/nvme\d+n\d+)p\d+$}) { $parent_disk = $1; }
elsif ($parent_disk =~ m{^(/dev/[a-z]+\d+)[ps]\d+.*$}) { $parent_disk = $1; }
elsif ($parent_disk =~ m{^(/dev/[a-z]+)\d+$}) { $parent_disk = $1; }

return ("-", "-", "-", "-") unless (-e $parent_disk);

my $model = "-";
my $serial = "-";
my $temp = "-";
my $size = "-";

if ($^O eq 'linux') {
    my $out = `lsblk -dno MODEL,SERIAL $parent_disk 2>/dev/null`;
    chomp $out;
    ($model, $serial) = split(/\s+/, $out, 2);
    if (!$model) {
         my $info = `smartctl -i $parent_disk 2>/dev/null`;
         if ($info =~ /Device Model:\s+(.*)/) { $model = $1; }
         elsif ($info =~ /Model Number:\s+(.*)/) { $model = $1; }
         if ($info =~ /Serial Number:\s+(.*)/) { $serial = $1; }
    }
    my $size_out = `lsblk -dno SIZE $dev_path 2>/dev/null`;
    chomp $size_out;
    if ($size_out) { $size = $size_out; }
} elsif ($^O eq 'freebsd') {
    my $smart = `smartctl -i $parent_disk 2>/dev/null`;
    if ($smart =~ /Device Model:\s+(.*)/) { $model = $1; }
    elsif ($smart =~ /Model Number:\s+(.*)/) { $model = $1; }
    if ($smart =~ /Serial Number:\s+(.*)/) { $serial = $1; }
    if ($model eq "-" && $serial eq "-") {
        # Fallback to diskinfo if smartctl fails
        my $diskinfo = `diskinfo -v $parent_disk 2>/dev/null`;
        if ($diskinfo =~ /^\s+(.*?)\s+# Disk descr\./m) { $model = $1; }
        if ($diskinfo =~ /^\s+(.*?)\s+# Disk ident\./m) { $serial = $1; }
    }
    my $diskinfo = `diskinfo -v $dev_path 2>/dev/null`;
    if ($diskinfo =~ /^\s+(\d+)\s+# mediasize in bytes/m) {
        $size = to_iec($1);
    }
}

# Get Temperature
my $smart_a = `smartctl -A $parent_disk 2>/dev/null`;
if ($smart_a =~ /^(190|194)\s+\w+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\d+)/m) {
    $temp = $2 . "C";
} elsif ($smart_a =~ /^Temperature:\s+(\d+)\s+Celsius/m) {
    $temp = $1 . "C";
}

$model ||= "-";
$serial ||= "-";
$temp ||= "-";
$size ||= "-";
return ($model, $serial, $temp, $size);
}

sub get_type_description {
    my ($type) = @_;
    my %type_map = (
        'freebsd'         => 'FreeBSD',
        'freebsd-ufs'     => 'FreeBSD UFS',
        'freebsd-swap'    => 'FreeBSD Swap',
        'freebsd-vinum'   => 'FreeBSD Vinum',
        'freebsd-zfs'     => 'FreeBSD ZFS',
        'freebsd-boot'    => 'FreeBSD Boot',
        'efi'             => 'EFI System',
        'bios-boot'       => 'BIOS Boot',
        'ms-basic-data'   => 'Microsoft Basic Data',
        'ms-reserved'     => 'Microsoft Reserved',
        'ms-recovery'     => 'Microsoft Recovery',
        'apple-ufs'       => 'Apple UFS',
        'apple-hfs'       => 'Apple HFS',
        'apple-boot'      => 'Apple Boot',
        'apple-raid'      => 'Apple RAID',
        'apple-label'     => 'Apple Label',
        'linux-data'      => 'Linux Data',
        'linux-swap'      => 'Linux Swap',
        'linux-lvm'       => 'Linux LVM',
        'linux-raid'      => 'Linux RAID',
    );
    return $type_map{$type} || $type;
}

sub get_disk_structure {
    my ($device) = @_;
    my $result = { 'entries' => [], 'partitions' => {} };
    my $cmd = "gpart show -l $device 2>&1";
    my $out = backquote_command($cmd);
    if ($out =~ /=>\s+(\d+)\s+(\d+)\s+(\S+)\s+(\S+)\s+\(([^)]+)\)/) {
        my $start_block = $1;
        my $size_blocks = $2;
        $result->{'total_blocks'} = $start_block + $size_blocks;
        $result->{'device_name'}  = $3;
        $result->{'scheme'}       = $4;
        $result->{'size_human'}   = $5;
    }
    foreach my $line (split(/\n/, $out)) {
        if ($line =~ /^\s+(\d+)\s+(\d+)\s+-\s+free\s+-\s+\(([^)]+)\)/) {
            push @{$result->{'entries'}}, {
                'start'      => $1,
                'size'       => $2,
                'size_human' => $3,
                'type'       => 'free'
            };
            next;
        }
        if ($line =~ /^\s+(\d+)\s+(\d+)\s+(\d+)\s+(\S+)(?:\s+\[[^\]]+\])?\s+\(([^)]+)\)/) {
            push @{$result->{'entries'}}, {
                'start'      => $1,
                'size'       => $2,
                'index'      => $3,
                'label'      => $4,
                'size_human' => $5,
                'type'       => 'partition'
            };
        }
    }
    my $list_out = backquote_command("gpart list $device 2>&1");
    my (%parts, $current_idx);
    foreach my $line (split(/\n/, $list_out)) {
        if ($line =~ /^\s*(?:\d+\.\s*)?Name:\s*(\S+)/i) {
            my $name = $1;
            if ($name =~ /[ps](\d+)$/) {
                $current_idx = int($1);
                $parts{$current_idx} ||= { name => $name };
            } else {
                undef $current_idx;
            }
        }
        elsif (defined $current_idx && $line =~ /^\s*label:\s*(\S+)/i) {
            $parts{$current_idx}->{'label'} = $1;
        }
        elsif (defined $current_idx && $line =~ /^\s*type:\s*(\S+)/i) {
            $parts{$current_idx}->{'type'} = $1;
        }
        elsif (defined $current_idx && $line =~ /^\s*rawtype:\s*(\S+)/i) {
            $parts{$current_idx}->{'rawtype'} = $1;
        }
        elsif (defined $current_idx && $line =~ /^\s*length:\s*(\d+)/i) {
            $parts{$current_idx}->{'length'} = $1;
        }
        elsif (defined $current_idx && $line =~ /^\s*offset:\s*(\d+)/i) {
            $parts{$current_idx}->{'offset'} = $1;
        }
        elsif ($line =~ /Sectorsize:\s*(\d+)/i) {
            $result->{'sectorsize'} = int($1);
        }
        elsif ($line =~ /Mediasize:\s*(\d+)/i) {
            $result->{'mediasize'} = int($1);
        }
    }
    $result->{'partitions'} = \%parts;
    foreach my $entry (@{$result->{'entries'}}) {
        next unless ($entry->{'type'} eq 'partition' && $entry->{'index'});
        my $idx = $entry->{'index'};
        if ($parts{$idx}) {
            if ($parts{$idx}->{'label'} && $parts{$idx}->{'label'} ne '(null)') {
                $entry->{'label'} = $parts{$idx}->{'label'};
            }
            $entry->{'part_type'} = $parts{$idx}->{'type'} || $parts{$idx}->{'rawtype'} || $entry->{'part_type'};
            $entry->{'rawtype'} = $parts{$idx}->{'rawtype'} if ($parts{$idx}->{'rawtype'});
        }
    }
    return $result;
}

sub get_disk_sectorsize {
    my ($device) = @_;
    my $dev = $device; $dev =~ s{^/dev/}{};
    my $outv = backquote_command("diskinfo -v $dev 2>/dev/null");
    if ($outv =~ /sectorsize:\s*(\d+)/i) {
        return int($1);
    }
    my $out = backquote_command("diskinfo $dev 2>/dev/null");
    if ($out =~ /^\S+\s+(\d+)\s+\d+/) {
        return int($1);
    }
    my $base = $dev;
    my $ds = get_disk_structure($base);
    if ($ds && $ds->{'sectorsize'}) { return int($ds->{'sectorsize'}); }
    return undef;
}

sub base_disk_device {
    my ($device) = @_;
    return undef unless $device;
    my $d = $device;
    $d =~ s{^/dev/}{};
    $d =~ s{(p|s)\d+.*$}{};
    return "/dev/$d";
}

sub build_zfs_devices_cache {
    my %pools;
    my %devices;
    my $cmd = "zpool status 2>&1";
    my $out = backquote_command($cmd);
    my ($current_pool, $in_config, $current_vdev_type, $current_vdev_group, 
        $is_mirrored, $is_raidz, $raidz_level, $is_single, $is_striped, $vdev_count);
    $current_vdev_type = 'data';
    foreach my $line (split(/\n/, $out)) {
        if ($line =~ /^\s*pool:\s+(\S+)/) {
            $current_pool = $1;
            $pools{$current_pool} = 1;
            $in_config = 0;
            $current_vdev_type = 'data';
        }
        elsif ($line =~ /^\s*config:/) {
            $in_config = 1;
            $current_vdev_group = undef;
            $is_mirrored = 0;
            $is_raidz = 0;
            $raidz_level = 0;
            $is_single = 0;
            $is_striped = 0;
            $vdev_count = 0;
        }
        elsif ($in_config and $line =~ /^\s+logs/) {
            $current_vdev_type = 'log';
            $current_vdev_group = undef;
        }
        elsif ($in_config and $line =~ /^\s+cache/) {
            $current_vdev_type = 'cache';
            $current_vdev_group = undef;
        }
        elsif ($in_config and $line =~ /^\s+spares/) {
            $current_vdev_type = 'spare';
            $current_vdev_group = undef;
        }
        elsif ($in_config and $line =~ /^\s+mirror-(\d+)/) {
            $current_vdev_group = "mirror-$1";
            $is_mirrored = 1;
            $is_raidz = 0;
            $is_single = 0;
            $is_striped = 0;
            $vdev_count = 0;
        }
        elsif ($in_config and $line =~ /^\s+raidz(\d+)?-(\d+)/) {
            $current_vdev_group = "raidz" . ($1 || "1") . "-$2";
            $is_mirrored = 0;
            $is_raidz = 1;
            $raidz_level = $1 || 1;
            $is_single = 0;
            $is_striped = 0;
            $vdev_count = 0;
        }
        elsif ($in_config and $line =~ /^\s+(\S+)\s+(\S+)/) {
            my $device = $1;
            my $state  = $2;
            next if ($device eq $current_pool or $device =~ /^mirror-/ or $device =~ /^raidz\d*-/);
            if ($current_vdev_group) { $vdev_count++; }
            else { $is_single = 1; }
            my $device_id = $device;
            $device_id = $1 if ($device =~ /^gpt\/(.*)/);
            $devices{$device} = {
                'pool'        => $current_pool,
                'vdev_type'   => $current_vdev_type,
                'is_mirrored' => $is_mirrored,
                'is_raidz'    => $is_raidz,
                'raidz_level' => $raidz_level,
                'is_single'   => $is_single,
                'is_striped'  => $is_striped,
                'vdev_group'  => $current_vdev_group,
                'vdev_count'  => $vdev_count
            };
            $devices{"gpt/$device"} = $devices{$device} if ($device !~ /^gpt\//);
            $devices{"/dev/$device"} = $devices{$device};
            if ($device !~ /^gpt\//) {
                $devices{"/dev/gpt/$device"} = $devices{$device};
            }
            $devices{lc($device)} = $devices{$device};
            if ($device !~ /^gpt\//) {
                $devices{"gpt/" . lc($device)} = $devices{$device};
                $devices{"/dev/gpt/" . lc($device)} = $devices{$device};
            }
        }
    }
    return (\%pools, \%devices);
}

sub _possible_partition_ids {
    my ($base_device, $scheme, $part_num, $part_name, $part_label) = @_;
    my @ids;
    if (defined $base_device && defined $part_num && length($base_device)) {
        my $sep = ($scheme && $scheme eq 'GPT') ? 'p' : 's';
        my $device_path = "/dev/$base_device" . $sep . $part_num;
        push(@ids, $device_path);
        (my $short = $device_path) =~ s/^\/dev\///;
        push(@ids, $short);
    }
    if ($part_name && $part_name ne '-') {
        push(@ids, $part_name, "/dev/$part_name");
    }
    if (defined $part_label && $part_label ne '-' && $part_label ne '(null)') {
        push(@ids, $part_label, "gpt/$part_label", "/dev/gpt/$part_label",
              lc($part_label), "gpt/".lc($part_label), "/dev/gpt/".lc($part_label));
        if ($part_label =~ /^(sLOG\w+)$/) {
            push(@ids, $1, "gpt/$1", "/dev/gpt/$1");
        }
    }
    return @ids;
}

sub _find_in_zfs {
    my ($zfs_devices, @ids) = @_;
    foreach my $id (@ids) {
        my $nid = lc($id);
        if ($zfs_devices->{$nid}) {
            return $zfs_devices->{$nid};
        }
    }
    return undef;
}

sub classify_partition_row {
    my (%args) = @_;
    my $ids = [ _possible_partition_ids(@args{qw/base_device scheme part_num part_name part_label/}) ];
    my $zdev = _find_in_zfs($args{'zfs_devices'}, @$ids);

    my $type_desc = $args{'entry_part_type'};
    if (!defined $type_desc || $type_desc eq '-' || $type_desc eq 'unknown') {
    }
    if (defined $type_desc && defined $args{'part_label'}) {
        my $pl = $args{'part_label'};
        if ($type_desc =~ m{^(?:/dev/)?gpt(?:id)?/\Q$pl\E$}i) {
            undef $type_desc;
        }
    }

    my ($format, $usage, $role) = ('-', $text{'part_nouse'} || 'Unused', '-');
    my $raw = lc($args{'entry_rawtype'} || '');
    my $t   = lc($type_desc || '');
    my %boot_guid = map { $_ => 1 } qw(
        c12a7328-f81f-11d2-ba4b-00a0c93ec93b
        21686148-6449-6e6f-744e-656564454649
        83bd6b9d-7f41-11dc-be0b-001560b84f0f
        49f48d5a-b10e-11dc-b99b-0019d1879648
        824cc7a0-36a8-11e3-890a-952519ad3f61
        426f6f74-0000-11aa-aa11-00306543ecac
    );
    my %boot_mbr = map { $_ => 1 } qw( 0xef 0xa0 0xa5 0xa6 0xa9 0xab );
    my $is_boot_type = ($t =~ /\b(efi|bios-?boot|freebsd-boot|netbsd-boot|openbsd-boot|apple-boot)\b/);
    my $is_boot_raw  = ($raw && ($boot_guid{$raw} || $boot_mbr{$raw}));
    if ($is_boot_type || $is_boot_raw) {
        my $fmt = ($t =~ /efi/ || $raw eq 'c12a7328-f81f-11d2-ba4b-00a0c93ec93b' || lc($raw) eq '0xef') ? get_type_description('efi') : get_type_description('freebsd-boot');
        my $boot_txt = $text{'disk_boot'} || 'Boot partition';
        my $role_txt = $text{'disk_boot_role'} || 'Booting system';
        return ($fmt, $boot_txt, $role_txt);
    }
    if ((!$args{'entry_part_type'} || $args{'entry_part_type'} eq '-' || $args{'entry_part_type'} eq 'unknown') && ($args{'part_num'}||'') eq '1') {
        my $sb = $args{'size_blocks'} || 0;
        if ($sb > 0) {
            my $base = base_disk_device('/dev/' . ($args{'base_device'}||''));
            my $ss = get_disk_sectorsize($base) || 512;
            my $bytes = $sb * $ss;
            if ($bytes <= 2*1024*1024) {
                return (get_type_description('freebsd-boot'), $text{'disk_boot'} || 'Boot partition', $text{'disk_boot_role'} || 'Booting system');
            }
        } elsif ($args{'size_human'} && $args{'size_human'} =~ /^(?:512k|1m|1\.0m)$/i) {
            return (get_type_description('freebsd-boot'), $text{'disk_boot'} || 'Boot partition', $text{'disk_boot_role'} || 'Booting system');
        }
    }
    if ($zdev) {
        $format = ($^O eq 'linux') ? 'ZFS' : 'FreeBSD ZFS';
        my $inzfs_txt   = $text{'disk_inzfs'} || 'In ZFS pool';
        my $z_mirror    = $text{'disk_zfs_mirror'} || 'ZFS Mirror';
        my $z_stripe    = $text{'disk_zfs_stripe'} || 'ZFS Stripe';
        my $z_single    = $text{'disk_zfs_single'} || 'ZFS Data';
        my $z_data      = $text{'disk_zfs_data'} || 'ZFS Data';
        my $z_log       = $text{'disk_zfs_log'} || 'ZFS Log';
        my $z_cache     = $text{'disk_zfs_cache'} || 'ZFS Cache';
        my $z_spare     = $text{'disk_zfs_spare'} || 'ZFS Spare';
        $usage  = $inzfs_txt . ' ' . $zdev->{'pool'};
        my $vt  = $zdev->{'vdev_type'};
        my $cnt = $zdev->{'vdev_count'} || 0;
        if ($vt eq 'log') { $role = $z_log; }
        elsif ($vt eq 'cache') { $role = $z_cache; }
        elsif ($vt eq 'spare') { $role = $z_spare; }
        elsif ($zdev->{'is_mirrored'}) {
            $role = $z_mirror;
            $role .= " ($cnt in group)" if $cnt;
        }
        elsif ($zdev->{'is_raidz'}) {
            my $lvl = $zdev->{'raidz_level'} || 1;
            $role = 'RAID-Z' . $lvl;
            $role .= " ($cnt in group)" if $cnt;
        }
        elsif ($zdev->{'is_striped'}) {
            $role = $z_stripe;
            $role .= " ($cnt in group)" if $cnt;
        }
        elsif ($zdev->{'is_single'}) { $role = $z_single; }
        else { $role = $z_data; }
        return ($format, $usage, $role);
    }

    if (defined $type_desc && $type_desc =~ /(?:freebsd|linux)-swap|^swap$/i) {
        $format = 'Swap';
        $usage = $text{'disk_swap'} || 'Swap device';
        $role = $text{'disk_swap_role'} || 'Swap memory';
    }
    elsif (defined $type_desc && $type_desc =~ /^zfs_member$/i) { $format = ($^O eq 'linux') ? 'ZFS' : 'FreeBSD ZFS'; }
    elsif (defined $type_desc && $type_desc =~ /^ext[234]$/i) { $format = uc($type_desc); }
    elsif (defined $type_desc && $type_desc =~ /^xfs$/i) { $format = 'XFS'; }
    elsif (defined $type_desc && $type_desc =~ /^btrfs$/i) { $format = 'Btrfs'; }
    elsif (defined $type_desc && $type_desc =~ /^vfat$/i) { $format = 'FAT'; }
    elsif (defined $type_desc && $type_desc =~ /linux-lvm/i) { $format = 'Linux LVM'; }
    elsif (defined $type_desc && $type_desc =~ /linux-raid/i) { $format = 'Linux RAID'; }
    elsif (defined $type_desc && $type_desc =~ /ntfs/i) { $format = 'NTFS'; }
    elsif (defined $type_desc && $type_desc =~ /fat32/i) { $format = 'FAT32'; }
    elsif (defined $type_desc && $type_desc =~ /fat|msdos/i) { $format = 'FAT'; }
    elsif (defined $type_desc && $type_desc =~ /ms-basic/i) { $format = 'FAT/NTFS'; }
    elsif ($raw ne '' && $raw =~ /^\d+$/) {
        my $code = int($raw);
        if ($code == 7) { $format = 'NTFS'; }
        elsif ($code == 11 || $code == 12) { $format = 'FAT32'; }
        elsif ($code == 6 || $code == 14) { $format = 'FAT'; }
    }
    elsif (defined $type_desc && $type_desc =~ /linux/i) { $format = 'Linux'; }
    elsif (defined $type_desc && $type_desc =~ /apple-ufs/i) { $format = 'Apple UFS'; }
    elsif (defined $type_desc && $type_desc =~ /apple-hfs/i) { $format = 'HFS+'; }
    elsif (defined $type_desc && $type_desc =~ /apple-raid/i) { $format = 'Apple RAID'; }
    elsif (defined $type_desc && $type_desc =~ /freebsd-ufs/i) { $format = 'FreeBSD UFS'; }
    elsif (defined $type_desc && $type_desc =~ /freebsd-zfs/i) { $format = 'FreeBSD ZFS'; }
    else {
        if (defined $args{'part_label'} && $args{'part_label'} =~ /^swap\d*$/i) {
            $format = 'Swap';
            $usage = $text{'disk_swap'} || 'Swap device';
            $role = $text{'disk_swap_role'} || 'Swap memory';
        }
    }
    return ($format, $usage, $role);
}
1;
